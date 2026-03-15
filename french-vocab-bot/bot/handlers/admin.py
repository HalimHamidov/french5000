"""Admin command handlers: /admin_* commands."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from bot.models.database import get_db
from bot.services.scheduler import (
    send_afternoon_lesson,
    send_evening_reminder,
    send_morning_review,
    send_weekly_summary,
)
from bot.utils.config import ADMIN_CHAT_ID, DATA_PATH, DB_PATH

logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id == ADMIN_CHAT_ID


def admin_only(func):
    """Decorator: reject non-admin users."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Admin only.")
            return
        return await func(update, context)
    wrapper.__name__ = func.__name__
    return wrapper


# ── /admin_schedule ───────────────────────────────────────────────────────────

@admin_only
async def cmd_admin_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from bot.utils.config import (
        AFTERNOON_LESSON_TIME,
        EVENING_REMINDER_TIME,
        MORNING_REVIEW_TIME,
        TIMEZONE,
        WEEKLY_SUMMARY_DAY,
    )
    await update.message.reply_text(
        "🗓 <b>Scheduled Tasks</b>\n\n"
        f"Timezone: <b>{TIMEZONE}</b>\n"
        f"Morning review: <b>{MORNING_REVIEW_TIME}</b>\n"
        f"Afternoon lesson: <b>{AFTERNOON_LESSON_TIME}</b>\n"
        f"Evening reminder: <b>{EVENING_REMINDER_TIME}</b>\n"
        f"Weekly summary day: <b>{WEEKLY_SUMMARY_DAY}</b>\n\n"
        "Use <code>.env</code> to change schedule timings.",
        parse_mode=ParseMode.HTML,
    )


# ── /admin_post_now ───────────────────────────────────────────────────────────

@admin_only
async def cmd_admin_post_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /admin_post_now <morning|afternoon|evening|weekly>"
        )
        return

    task = args[0].lower()
    bot = context.bot

    if task == "morning":
        await send_morning_review(bot)
        await update.message.reply_text("✅ Morning review sent.")
    elif task == "afternoon":
        await send_afternoon_lesson(bot)
        await update.message.reply_text("✅ Afternoon lesson sent.")
    elif task == "evening":
        await send_evening_reminder(bot)
        await update.message.reply_text("✅ Evening reminder sent.")
    elif task == "weekly":
        await send_weekly_summary(bot)
        await update.message.reply_text("✅ Weekly summary sent.")
    else:
        await update.message.reply_text(
            "Unknown task. Use: morning | afternoon | evening | weekly"
        )


# ── /admin_import_json ────────────────────────────────────────────────────────

@admin_only
async def cmd_admin_import_json(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger a fresh import of the JSON word data into SQLite."""
    await update.message.reply_text("⏳ Importing words from JSON... please wait.")

    try:
        count = await _import_words_from_json(DATA_PATH, DB_PATH)
        await update.message.reply_text(
            f"✅ Import complete. <b>{count}</b> words upserted into the database.",
            parse_mode=ParseMode.HTML,
        )
    except Exception as exc:
        logger.exception("Import failed")
        await update.message.reply_text(f"❌ Import failed: {exc}")


async def _import_words_from_json(data_path: Path, db_path: Path) -> int:
    """Read JSON and upsert words into the words table. Returns count."""
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected a JSON array at the top level.")

    count = 0
    async with await get_db(db_path) as db:
        for item in data:
            rank = item.get("rank")
            if rank is None or not (1 <= rank <= 5000):
                continue
            collocations = item.get("collocations") or []
            collocations_json = json.dumps(collocations, ensure_ascii=False)

            await db.execute(
                """
                INSERT INTO words
                    (id, rank, word, pos, translation_en, example_fr, example_en,
                     dispersion, frequency, semantic_cluster, collocations, audio, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(rank) DO UPDATE SET
                    word             = excluded.word,
                    pos              = excluded.pos,
                    translation_en   = excluded.translation_en,
                    example_fr       = excluded.example_fr,
                    example_en       = excluded.example_en,
                    dispersion       = excluded.dispersion,
                    frequency        = excluded.frequency,
                    semantic_cluster = excluded.semantic_cluster,
                    collocations     = excluded.collocations,
                    audio            = excluded.audio,
                    notes            = excluded.notes
                """,
                (
                    item.get("id"),
                    rank,
                    item.get("word", ""),
                    item.get("pos"),
                    item.get("translation_en"),
                    item.get("example_fr"),
                    item.get("example_en"),
                    item.get("dispersion"),
                    item.get("frequency"),
                    item.get("semantic_cluster"),
                    collocations_json,
                    item.get("audio"),
                    item.get("notes"),
                ),
            )
            count += 1
        await db.commit()
    return count


# ── /admin_set_rate ────────────────────────────────────────────────────────────

@admin_only
async def cmd_admin_set_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set global words_per_day for all users."""
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /admin_set_rate <12-15>")
        return
    wpd = int(args[0])
    if not (12 <= wpd <= 15):
        await update.message.reply_text("Rate must be 12-15.")
        return

    async with await get_db(DB_PATH) as db:
        await db.execute("UPDATE user_settings SET words_per_day=?", (wpd,))
        await db.commit()
    await update.message.reply_text(f"✅ All users' words_per_day set to {wpd}.")


# ── /admin_reschedule ─────────────────────────────────────────────────────────

@admin_only
async def cmd_admin_reschedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset a user's due dates — reschedule all their reviews to today."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /admin_reschedule <user_id>\n"
            "This resets all review due dates to today for that user."
        )
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("Invalid user_id.")
        return

    from datetime import date
    today = date.today().isoformat()
    async with await get_db(DB_PATH) as db:
        await db.execute(
            "UPDATE user_progress SET next_review_date=? WHERE user_id=?",
            (today, target_user_id),
        )
        await db.commit()
    await update.message.reply_text(
        f"✅ All reviews for user {target_user_id} rescheduled to today."
    )


# ── /admin_broadcast ──────────────────────────────────────────────────────────

@admin_only
async def cmd_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast a message to all registered users."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /admin_broadcast <message text>\n"
            "The message will be sent to all users."
        )
        return

    message_text = " ".join(context.args)
    async with await get_db(DB_PATH) as db:
        rows = await db.execute_fetchall("SELECT user_id FROM user_settings")
    user_ids = [r["user_id"] for r in rows]

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 <b>Admin Message</b>\n\n{message_text}",
                parse_mode=ParseMode.HTML,
            )
            sent += 1
        except Exception as exc:
            logger.warning("Broadcast failed for %s: %s", uid, exc)
            failed += 1

    await update.message.reply_text(
        f"✅ Broadcast sent: {sent} succeeded, {failed} failed."
    )


# ── /admin_stats ───────────────────────────────────────────────────────────────

@admin_only
async def cmd_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show overall database statistics."""
    async with await get_db(DB_PATH) as db:
        words_count = (await db.execute_fetchall("SELECT COUNT(*) as c FROM words"))[0]["c"]
        users_count = (await db.execute_fetchall("SELECT COUNT(*) as c FROM user_settings"))[0]["c"]
        progress_count = (await db.execute_fetchall("SELECT COUNT(*) as c FROM user_progress"))[0]["c"]
        submissions_count = (await db.execute_fetchall("SELECT COUNT(*) as c FROM submissions"))[0]["c"]

    await update.message.reply_text(
        "📊 <b>Admin Stats</b>\n\n"
        f"Words in DB: <b>{words_count}</b>\n"
        f"Registered users: <b>{users_count}</b>\n"
        f"Progress records: <b>{progress_count}</b>\n"
        f"Submissions: <b>{submissions_count}</b>",
        parse_mode=ParseMode.HTML,
    )


def register_admin_handlers(app) -> None:
    app.add_handler(CommandHandler("admin_schedule", cmd_admin_schedule))
    app.add_handler(CommandHandler("admin_post_now", cmd_admin_post_now))
    app.add_handler(CommandHandler("admin_import_json", cmd_admin_import_json))
    app.add_handler(CommandHandler("admin_set_rate", cmd_admin_set_rate))
    app.add_handler(CommandHandler("admin_reschedule", cmd_admin_reschedule))
    app.add_handler(CommandHandler("admin_broadcast", cmd_admin_broadcast))
    app.add_handler(CommandHandler("admin_stats", cmd_admin_stats))
