"""User progress tracking service."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from bot.models.database import get_db, row_to_dict
from bot.utils.config import DB_PATH

logger = logging.getLogger(__name__)


async def ensure_user_settings(user_id: int, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Ensure a user_settings row exists; return the row."""
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM user_settings WHERE user_id=?", (user_id,)
        )
        if not rows:
            await db.execute(
                "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,)
            )
            await db.commit()
            rows = await db.execute_fetchall(
                "SELECT * FROM user_settings WHERE user_id=?", (user_id,)
            )
    return row_to_dict(rows[0]) if rows else {}


async def get_user_settings(user_id: int, db_path: Path = DB_PATH) -> dict[str, Any]:
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM user_settings WHERE user_id=?", (user_id,)
        )
    return row_to_dict(rows[0]) if rows else {}


async def update_user_settings(
    user_id: int, updates: dict[str, Any], db_path: Path = DB_PATH
) -> None:
    if not updates:
        return
    allowed = {"words_per_day", "lang", "reminder_time", "cluster_mode"}
    filtered = {k: v for k, v in updates.items() if k in allowed}
    if not filtered:
        return
    set_clause = ", ".join(f"{k}=?" for k in filtered)
    values = list(filtered.values()) + [user_id]
    async with await get_db(db_path) as db:
        await db.execute(
            f"UPDATE user_settings SET {set_clause} WHERE user_id=?", values
        )
        await db.commit()


async def get_or_create_daily(
    user_id: int, day: date | None = None, db_path: Path = DB_PATH
) -> dict[str, Any]:
    """Return today's daily_schedule row, creating it if needed."""
    if day is None:
        day = date.today()
    day_str = day.isoformat()
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM daily_schedule WHERE user_id=? AND date=?",
            (user_id, day_str),
        )
        if not rows:
            await db.execute(
                "INSERT OR IGNORE INTO daily_schedule (user_id, date) VALUES (?, ?)",
                (user_id, day_str),
            )
            await db.commit()
            rows = await db.execute_fetchall(
                "SELECT * FROM daily_schedule WHERE user_id=? AND date=?",
                (user_id, day_str),
            )
    return row_to_dict(rows[0]) if rows else {}


async def increment_daily(
    user_id: int,
    field: str,
    amount: int = 1,
    db_path: Path = DB_PATH,
) -> None:
    """Increment a counter field in today's daily_schedule row."""
    allowed = {"new_words_done", "reviews_done", "sentences_done", "story_done", "paragraph_done"}
    if field not in allowed:
        raise ValueError(f"Unknown daily field: {field}")
    day_str = date.today().isoformat()
    await get_or_create_daily(user_id, db_path=db_path)
    async with await get_db(db_path) as db:
        await db.execute(
            f"UPDATE daily_schedule SET {field} = {field} + ? WHERE user_id=? AND date=?",
            (amount, user_id, day_str),
        )
        await db.commit()


async def set_daily_flag(
    user_id: int, field: str, value: int = 1, db_path: Path = DB_PATH
) -> None:
    """Set a boolean flag (0/1) in today's daily_schedule."""
    allowed = {"story_done", "paragraph_done"}
    if field not in allowed:
        raise ValueError(f"Unknown flag field: {field}")
    day_str = date.today().isoformat()
    await get_or_create_daily(user_id, db_path=db_path)
    async with await get_db(db_path) as db:
        await db.execute(
            f"UPDATE daily_schedule SET {field}=? WHERE user_id=? AND date=?",
            (value, user_id, day_str),
        )
        await db.commit()


async def add_submission(
    user_id: int,
    text: str,
    submission_type: str,
    word_id: int | None = None,
    db_path: Path = DB_PATH,
) -> None:
    """Save a sentence, story, or paragraph submission."""
    async with await get_db(db_path) as db:
        await db.execute(
            "INSERT INTO submissions (user_id, word_id, type, text) VALUES (?, ?, ?, ?)",
            (user_id, word_id, submission_type, text),
        )
        await db.commit()


async def get_user_stats(user_id: int, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Compute aggregate stats for a user."""
    today = date.today()
    week_ago = (today - timedelta(days=7)).isoformat()
    today_str = today.isoformat()

    async with await get_db(db_path) as db:
        # Total words introduced
        r = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM user_progress WHERE user_id=?", (user_id,)
        )
        total_words = r[0]["cnt"] if r else 0

        # Total reviews done
        r = await db.execute_fetchall(
            "SELECT COALESCE(SUM(reviews_done), 0) as cnt FROM daily_schedule WHERE user_id=?",
            (user_id,),
        )
        total_reviews = r[0]["cnt"] if r else 0

        # Mastered words (review_count >= 5)
        r = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM user_progress WHERE user_id=? AND review_count >= 5",
            (user_id,),
        )
        mastered = r[0]["cnt"] if r else 0

        # Week stats
        r = await db.execute_fetchall(
            """
            SELECT COALESCE(SUM(new_words_done), 0) as nw,
                   COALESCE(SUM(reviews_done), 0) as rv,
                   COALESCE(SUM(sentences_done), 0) as sn,
                   COALESCE(SUM(story_done), 0) as st
            FROM daily_schedule
            WHERE user_id=? AND date >= ?
            """,
            (user_id, week_ago),
        )
        week_new = r[0]["nw"] if r else 0
        week_reviews = r[0]["rv"] if r else 0
        week_sentences = r[0]["sn"] if r else 0
        week_stories = r[0]["st"] if r else 0

        # Streak — count consecutive days going back from today with any activity
        streak = await _compute_streak(db, user_id, today)

        # Since date
        r = await db.execute_fetchall(
            "SELECT MIN(introduced_at) as dt FROM user_progress WHERE user_id=?",
            (user_id,),
        )
        since = r[0]["dt"] if r and r[0]["dt"] else "N/A"

    return {
        "total_words": total_words,
        "total_reviews": total_reviews,
        "mastered": mastered,
        "week_new": week_new,
        "week_reviews": week_reviews,
        "week_sentences": week_sentences,
        "week_stories": week_stories,
        "streak": streak,
        "since": since,
    }


async def _compute_streak(db: Any, user_id: int, today: date) -> int:
    """Count consecutive active days ending today."""
    streak = 0
    check = today
    for _ in range(365):
        rows = await db.execute_fetchall(
            """
            SELECT (new_words_done + reviews_done + sentences_done + story_done) as activity
            FROM daily_schedule
            WHERE user_id=? AND date=?
            """,
            (user_id, check.isoformat()),
        )
        if rows and rows[0]["activity"] > 0:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak
