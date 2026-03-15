#!/usr/bin/env python3
"""
schedule_daily.py — Standalone cron-style runner for scheduled tasks.

This script can be called by an external cron job or task scheduler
to trigger specific bot tasks without keeping the full bot running.

Usage:
    python scripts/schedule_daily.py morning
    python scripts/schedule_daily.py afternoon
    python scripts/schedule_daily.py evening
    python scripts/schedule_daily.py weekly

The BOT_TOKEN must be set in the .env file at the project root.
"""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

VALID_TASKS = ("morning", "afternoon", "evening", "weekly")


async def run_task(task: str) -> None:
    from telegram import Bot
    from bot.utils.config import BOT_TOKEN
    from bot.models.database import init_db, DB_PATH

    await init_db(DB_PATH)

    async with Bot(token=BOT_TOKEN) as bot:
        if task == "morning":
            from bot.services.scheduler import send_morning_review
            await send_morning_review(bot)
        elif task == "afternoon":
            from bot.services.scheduler import send_afternoon_lesson
            await send_afternoon_lesson(bot)
        elif task == "evening":
            from bot.services.scheduler import send_evening_reminder
            await send_evening_reminder(bot)
        elif task == "weekly":
            from bot.services.scheduler import send_weekly_summary
            await send_weekly_summary(bot)

    logger.info("Task '%s' completed.", task)


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in VALID_TASKS:
        print(f"Usage: schedule_daily.py <{'|'.join(VALID_TASKS)}>")
        sys.exit(1)

    task = sys.argv[1]
    asyncio.run(run_task(task))


if __name__ == "__main__":
    main()
