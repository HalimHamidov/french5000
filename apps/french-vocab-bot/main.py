#!/usr/bin/env python3
"""
main.py — Entry point for the French Vocabulary Telegram Bot.

Steps:
1. Load .env configuration
2. Initialize SQLite database
3. Import words from JSON (if DB is empty)
4. Register all handlers
5. Build APScheduler for timed broadcasts
6. Start polling
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Silence noisy libraries ───────────────────────────────────────────────────
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def post_init(application) -> None:
    """Called once after the Application is built and before polling starts."""
    from bot.models.database import init_db
    from bot.services.scheduler import build_scheduler
    from bot.utils.config import DATA_PATH, DB_PATH

    # 1. Init DB
    await init_db(DB_PATH)
    logger.info("Database ready at %s", DB_PATH)

    # 2. Auto-import if words table is empty
    from bot.models.database import get_db
    async with await get_db(DB_PATH) as db:
        rows = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM words")
        word_count = rows[0]["cnt"] if rows else 0

    if word_count == 0:
        logger.info("Words table is empty — importing from %s", DATA_PATH)
        if DATA_PATH.exists():
            from scripts.import_words import import_words
            count = await import_words(DATA_PATH, DB_PATH)
            logger.info("Auto-imported %d words.", count)
        else:
            logger.warning(
                "Data file not found at %s. Run scripts/import_words.py manually.", DATA_PATH
            )
    else:
        logger.info("Words table has %d entries — skipping auto-import.", word_count)

    # 3. Start scheduler
    bot = application.bot
    scheduler = build_scheduler(bot)
    scheduler.start()
    logger.info("Scheduler started.")

    # Store scheduler reference for shutdown
    application.bot_data["scheduler"] = scheduler


async def post_shutdown(application) -> None:
    """Graceful shutdown."""
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")


def main() -> None:
    from telegram.ext import Application

    from bot.utils.config import BOT_TOKEN
    from bot.handlers.learner import register_learner_handlers
    from bot.handlers.quiz import register_quiz_handlers
    from bot.handlers.writing import register_writing_handlers
    from bot.handlers.admin import register_admin_handlers

    logger.info("Starting French Vocabulary Bot…")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register handlers
    register_learner_handlers(app)
    register_quiz_handlers(app)
    register_writing_handlers(app)
    register_admin_handlers(app)

    logger.info("All handlers registered. Starting polling…")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
