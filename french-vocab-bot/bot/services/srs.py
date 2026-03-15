"""Spaced Repetition System (SRS) engine.

Quality scores (matching Anki's SuperMemo SM-2 convention):
    0 = Again  (complete blackout / wrong)
    1 = Hard   (correct but very difficult)
    2 = Good   (correct with some effort)
    3 = Easy   (correct, easy)

Intervals: [0, 1, 3, 7, 16, 35, 60] days
The interval index advances or regresses based on quality.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

from bot.models.database import get_db, row_to_dict
from bot.utils.config import DB_PATH, SRS_INTERVALS

logger = logging.getLogger(__name__)

QUALITY_AGAIN = 0
QUALITY_HARD = 1
QUALITY_GOOD = 2
QUALITY_EASY = 3


def _next_interval(current_interval: int, quality: int) -> int:
    """
    Compute next interval in days based on current interval and quality.
    Uses a simplified SM-2-inspired algorithm with fixed interval steps.
    """
    # Map current interval to the nearest index in SRS_INTERVALS
    intervals = SRS_INTERVALS  # [0, 1, 3, 7, 16, 35, 60]

    # Find current position
    idx = 0
    for i, v in enumerate(intervals):
        if current_interval >= v:
            idx = i

    if quality == QUALITY_AGAIN:
        # Reset to beginning
        return intervals[1]  # next day
    elif quality == QUALITY_HARD:
        # Stay at same step or go back one
        new_idx = max(1, idx)
        return intervals[new_idx]
    elif quality == QUALITY_GOOD:
        # Advance one step
        new_idx = min(idx + 1, len(intervals) - 1)
        return intervals[new_idx]
    else:  # EASY
        # Advance two steps
        new_idx = min(idx + 2, len(intervals) - 1)
        return intervals[new_idx]


def next_review_date(current_interval: int, quality: int) -> date:
    """Return the date when the word should next be reviewed."""
    interval = _next_interval(current_interval, quality)
    return date.today() + timedelta(days=interval)


async def record_review(
    user_id: int,
    word_id: int,
    quality: int,
    db_path: Path = DB_PATH,
) -> None:
    """Update user_progress after a review with the given quality score."""
    async with await get_db(db_path) as db:
        row = await db.execute_fetchall(
            "SELECT * FROM user_progress WHERE user_id=? AND word_id=?",
            (user_id, word_id),
        )
        if not row:
            logger.warning("No progress row found for user=%s word=%s", user_id, word_id)
            return

        progress = row_to_dict(row[0])
        current_interval = progress.get("interval_days", 0)
        review_count = progress.get("review_count", 0) + 1
        new_interval = _next_interval(current_interval, quality)
        nrd = (date.today() + timedelta(days=new_interval)).isoformat()

        await db.execute(
            """
            UPDATE user_progress
            SET next_review_date=?, interval_days=?, review_count=?, last_quality=?
            WHERE user_id=? AND word_id=?
            """,
            (nrd, new_interval, review_count, quality, user_id, word_id),
        )
        await db.commit()
    logger.debug(
        "Review recorded: user=%s word=%s quality=%s next=%s",
        user_id, word_id, quality, nrd,
    )


async def introduce_word(
    user_id: int,
    word_id: int,
    db_path: Path = DB_PATH,
) -> None:
    """Mark a word as introduced (add to user_progress with Day 0)."""
    # Day 0: first review is tomorrow
    nrd = (date.today() + timedelta(days=1)).isoformat()
    async with await get_db(db_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO user_progress
                (user_id, word_id, next_review_date, interval_days, ease_factor, review_count, last_quality)
            VALUES (?, ?, ?, 0, 2.5, 0, NULL)
            """,
            (user_id, word_id, nrd),
        )
        await db.commit()


async def get_due_words(
    user_id: int,
    limit: int = 50,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """Return words due for review today (next_review_date <= today)."""
    today = date.today().isoformat()
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            """
            SELECT w.*, up.interval_days, up.review_count, up.last_quality, up.next_review_date
            FROM user_progress up
            JOIN words w ON w.id = up.word_id
            WHERE up.user_id = ?
              AND up.next_review_date <= ?
            ORDER BY up.next_review_date ASC, up.interval_days ASC
            LIMIT ?
            """,
            (user_id, today, limit),
        )
    return [row_to_dict(r) for r in rows]


async def get_due_count(user_id: int, db_path: Path = DB_PATH) -> int:
    """Return count of words due for review today."""
    today = date.today().isoformat()
    async with await get_db(db_path) as db:
        row = await db.execute_fetchall(
            "SELECT COUNT(*) as cnt FROM user_progress WHERE user_id=? AND next_review_date<=?",
            (user_id, today),
        )
    return row[0]["cnt"] if row else 0
