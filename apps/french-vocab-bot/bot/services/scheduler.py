"""Daily and weekly scheduling logic using APScheduler."""
from __future__ import annotations

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode

from bot.services.progress import get_or_create_daily, get_user_stats
from bot.services.srs import get_due_count, get_due_words
from bot.services.vocabulary import get_recent_words, get_today_new_words
from bot.utils.config import (
    ADMIN_CHAT_ID,
    AFTERNOON_LESSON_TIME,
    DB_PATH,
    EVENING_REMINDER_TIME,
    MORNING_REVIEW_TIME,
    TIMEZONE,
    WEEKLY_SUMMARY_DAY,
    WORDS_PER_DAY,
)
from bot.utils.formatter import (
    format_evening_reminder,
    format_morning_notification,
    format_weekly_paragraph_prompt,
    format_weekly_stats,
    format_word_list,
)

logger = logging.getLogger(__name__)


def _parse_time(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' into (hour, minute)."""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


async def _get_all_user_ids(db_path=DB_PATH) -> list[int]:
    """Return all user IDs from user_settings."""
    from bot.models.database import get_db
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall("SELECT user_id FROM user_settings")
    return [r["user_id"] for r in rows]


async def send_morning_review(bot: Bot) -> None:
    """Send morning review notification to all users."""
    user_ids = await _get_all_user_ids()
    for user_id in user_ids:
        try:
            count = await get_due_count(user_id)
            msg = format_morning_notification(count)
            await bot.send_message(
                chat_id=user_id, text=msg, parse_mode=ParseMode.HTML
            )
            logger.info("Sent morning notification to %s (%d due)", user_id, count)
        except Exception as exc:
            logger.error("Failed morning notification for %s: %s", user_id, exc)


async def send_afternoon_lesson(bot: Bot) -> None:
    """Send new words lesson to all users in the afternoon."""
    from bot.services.srs import introduce_word

    user_ids = await _get_all_user_ids()
    for user_id in user_ids:
        try:
            from bot.services.progress import get_user_settings

            settings = await get_user_settings(user_id)
            wpd = settings.get("words_per_day", WORDS_PER_DAY)
            words = await get_today_new_words(user_id, wpd)
            if not words:
                await bot.send_message(
                    chat_id=user_id,
                    text="🎉 No new words today — you've learned them all!",
                )
                continue

            # Introduce words into SRS
            for w in words:
                await introduce_word(user_id, w["id"])

            header = f"📚 <b>Today's {len(words)} New Words</b>\n\n"
            body = format_word_list(words)
            await bot.send_message(
                chat_id=user_id,
                text=header + body,
                parse_mode=ParseMode.HTML,
            )
            logger.info("Sent lesson to %s (%d words)", user_id, len(words))
        except Exception as exc:
            logger.error("Failed afternoon lesson for %s: %s", user_id, exc)


async def send_evening_reminder(bot: Bot) -> None:
    """Send evening reminder if daily tasks are incomplete."""
    user_ids = await _get_all_user_ids()
    for user_id in user_ids:
        try:
            from bot.services.progress import get_user_settings

            settings = await get_user_settings(user_id)
            wpd = settings.get("words_per_day", WORDS_PER_DAY)
            daily = await get_or_create_daily(user_id)
            due = await get_due_count(user_id)

            new_done = daily.get("new_words_done", 0) >= wpd
            msg = format_evening_reminder(
                new_done=new_done,
                review_count=due,
                sentences_done=daily.get("sentences_done", 0),
                story_done=bool(daily.get("story_done", 0)),
            )
            await bot.send_message(
                chat_id=user_id, text=msg, parse_mode=ParseMode.HTML
            )
        except Exception as exc:
            logger.error("Failed evening reminder for %s: %s", user_id, exc)


async def send_weekly_summary(bot: Bot) -> None:
    """Send weekly summary and paragraph task on the configured day."""
    user_ids = await _get_all_user_ids()
    for user_id in user_ids:
        try:
            stats = await get_user_stats(user_id)
            msg = format_weekly_stats(stats)
            await bot.send_message(
                chat_id=user_id, text=msg, parse_mode=ParseMode.HTML
            )

            # Also send paragraph task
            recent = await get_recent_words(user_id, days=7)
            if recent:
                para_msg = format_weekly_paragraph_prompt(recent)
                await bot.send_message(
                    chat_id=user_id, text=para_msg, parse_mode=ParseMode.HTML
                )
        except Exception as exc:
            logger.error("Failed weekly summary for %s: %s", user_id, exc)


def build_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Build and return configured APScheduler instance."""
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    morning_h, morning_m = _parse_time(MORNING_REVIEW_TIME)
    afternoon_h, afternoon_m = _parse_time(AFTERNOON_LESSON_TIME)
    evening_h, evening_m = _parse_time(EVENING_REMINDER_TIME)

    # Day-of-week map for APScheduler
    dow_map = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
    }
    weekly_dow = dow_map.get(WEEKLY_SUMMARY_DAY, "sun")

    scheduler.add_job(
        send_morning_review,
        CronTrigger(hour=morning_h, minute=morning_m, timezone=TIMEZONE),
        args=[bot],
        id="morning_review",
        replace_existing=True,
    )
    scheduler.add_job(
        send_afternoon_lesson,
        CronTrigger(hour=afternoon_h, minute=afternoon_m, timezone=TIMEZONE),
        args=[bot],
        id="afternoon_lesson",
        replace_existing=True,
    )
    scheduler.add_job(
        send_evening_reminder,
        CronTrigger(hour=evening_h, minute=evening_m, timezone=TIMEZONE),
        args=[bot],
        id="evening_reminder",
        replace_existing=True,
    )
    scheduler.add_job(
        send_weekly_summary,
        CronTrigger(day_of_week=weekly_dow, hour=morning_h, minute=morning_m, timezone=TIMEZONE),
        args=[bot],
        id="weekly_summary",
        replace_existing=True,
    )

    logger.info(
        "Scheduler configured: morning=%02d:%02d, afternoon=%02d:%02d, "
        "evening=%02d:%02d, weekly=%s",
        morning_h, morning_m, afternoon_h, afternoon_m,
        evening_h, evening_m, weekly_dow,
    )
    return scheduler
