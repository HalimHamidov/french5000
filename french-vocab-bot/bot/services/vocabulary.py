"""Vocabulary service — word selection, cluster logic, and word retrieval."""
from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any

import aiosqlite

from bot.models.database import get_db, row_to_dict
from bot.utils.config import DB_PATH

logger = logging.getLogger(__name__)


async def get_word_by_id(word_id: int, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM words WHERE id=?", (word_id,)
        )
    return row_to_dict(rows[0]) if rows else None


async def get_words_by_ids(
    word_ids: list[int], db_path: Path = DB_PATH
) -> list[dict[str, Any]]:
    if not word_ids:
        return []
    placeholders = ",".join("?" * len(word_ids))
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            f"SELECT * FROM words WHERE id IN ({placeholders})", word_ids
        )
    return [row_to_dict(r) for r in rows]


async def get_next_new_words(
    user_id: int,
    count: int = 12,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """
    Return the next `count` unseen words for the user, in frequency rank order.
    Words already in user_progress (introduced) are excluded.
    """
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            """
            SELECT w.*
            FROM words w
            WHERE w.id NOT IN (
                SELECT word_id FROM user_progress WHERE user_id=?
            )
            ORDER BY w.rank ASC
            LIMIT ?
            """,
            (user_id, count),
        )
    return [row_to_dict(r) for r in rows]


async def get_today_new_words(
    user_id: int,
    words_per_day: int,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """
    Return today's new words. These are words introduced today (present in
    user_progress with introduced_at = today) or the next unseen ones if
    today's set hasn't been started yet.
    """
    from datetime import date

    today = date.today().isoformat()
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            """
            SELECT w.*
            FROM user_progress up
            JOIN words w ON w.id = up.word_id
            WHERE up.user_id = ?
              AND up.introduced_at = ?
            ORDER BY w.rank ASC
            LIMIT ?
            """,
            (user_id, today, words_per_day),
        )
    if rows:
        return [row_to_dict(r) for r in rows]
    # Not yet started today — return next unseen words
    return await get_next_new_words(user_id, words_per_day, db_path)


async def get_recent_words(
    user_id: int,
    days: int = 7,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """Return words introduced in the last `days` days."""
    from datetime import date, timedelta

    cutoff = (date.today() - timedelta(days=days)).isoformat()
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            """
            SELECT w.*
            FROM user_progress up
            JOIN words w ON w.id = up.word_id
            WHERE up.user_id = ?
              AND up.introduced_at >= ?
            ORDER BY w.rank ASC
            """,
            (user_id, cutoff),
        )
    return [row_to_dict(r) for r in rows]


async def get_cluster_words(
    cluster_name: str,
    user_id: int | None = None,
    limit: int = 20,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """
    Return words from a semantic cluster.
    If user_id provided, only return words already introduced to that user.
    """
    async with await get_db(db_path) as db:
        if user_id is not None:
            rows = await db.execute_fetchall(
                """
                SELECT w.*
                FROM words w
                JOIN user_progress up ON up.word_id = w.id
                WHERE w.semantic_cluster = ?
                  AND up.user_id = ?
                ORDER BY w.rank ASC
                LIMIT ?
                """,
                (cluster_name, user_id, limit),
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM words WHERE semantic_cluster=? ORDER BY rank ASC LIMIT ?",
                (cluster_name, limit),
            )
    return [row_to_dict(r) for r in rows]


async def get_all_clusters(db_path: Path = DB_PATH) -> list[str]:
    """Return all distinct semantic cluster names."""
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            "SELECT DISTINCT semantic_cluster FROM words WHERE semantic_cluster IS NOT NULL ORDER BY semantic_cluster"
        )
    return [r["semantic_cluster"] for r in rows]


async def get_random_distractors(
    correct_word: dict[str, Any],
    count: int = 3,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """
    Return `count` distractor words (different pos or random) for quiz choices.
    Prefers words with the same part of speech for plausibility.
    """
    pos = correct_word.get("pos", "")
    word_id = correct_word.get("id")

    async with await get_db(db_path) as db:
        # Try same POS first
        rows = await db.execute_fetchall(
            """
            SELECT * FROM words
            WHERE id != ?
              AND pos = ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (word_id, pos, count * 2),
        )
        if len(rows) < count:
            # Fall back to any words
            rows = await db.execute_fetchall(
                "SELECT * FROM words WHERE id != ? ORDER BY RANDOM() LIMIT ?",
                (word_id, count * 2),
            )

    sample = random.sample(list(rows), min(count, len(rows)))
    return [row_to_dict(r) for r in sample]


async def get_total_word_count(db_path: Path = DB_PATH) -> int:
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM words")
    return rows[0]["cnt"] if rows else 0


async def search_words(query: str, limit: int = 10, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Search words by French word or English translation (partial match)."""
    pattern = f"%{query}%"
    async with await get_db(db_path) as db:
        rows = await db.execute_fetchall(
            """
            SELECT * FROM words
            WHERE word LIKE ? OR translation_en LIKE ?
            ORDER BY rank ASC
            LIMIT ?
            """,
            (pattern, pattern, limit),
        )
    return [row_to_dict(r) for r in rows]
