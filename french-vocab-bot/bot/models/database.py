"""SQLite database setup and all table definitions."""
import json
import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# SQL for all table creation
_CREATE_WORDS = """
CREATE TABLE IF NOT EXISTS words (
    id               INTEGER PRIMARY KEY,
    rank             INTEGER NOT NULL UNIQUE,
    word             TEXT    NOT NULL,
    pos              TEXT,
    translation_en   TEXT,
    example_fr       TEXT,
    example_en       TEXT,
    dispersion       REAL,
    frequency        INTEGER,
    semantic_cluster TEXT,
    collocations     TEXT,   -- JSON array stored as text
    audio            TEXT,
    notes            TEXT
);
"""

_CREATE_USER_PROGRESS = """
CREATE TABLE IF NOT EXISTS user_progress (
    user_id          INTEGER NOT NULL,
    word_id          INTEGER NOT NULL,
    next_review_date TEXT    NOT NULL,   -- ISO date YYYY-MM-DD
    interval_days    INTEGER NOT NULL DEFAULT 0,
    ease_factor      REAL    NOT NULL DEFAULT 2.5,
    review_count     INTEGER NOT NULL DEFAULT 0,
    last_quality     INTEGER,            -- 0-4 (Again/Hard/Good/Easy/Perfect)
    introduced_at    TEXT    NOT NULL DEFAULT (date('now')),
    PRIMARY KEY (user_id, word_id),
    FOREIGN KEY (word_id) REFERENCES words(id)
);
"""

_CREATE_DAILY_SCHEDULE = """
CREATE TABLE IF NOT EXISTS daily_schedule (
    user_id         INTEGER NOT NULL,
    date            TEXT    NOT NULL,   -- ISO date YYYY-MM-DD
    new_words_done  INTEGER NOT NULL DEFAULT 0,
    reviews_done    INTEGER NOT NULL DEFAULT 0,
    sentences_done  INTEGER NOT NULL DEFAULT 0,
    story_done      INTEGER NOT NULL DEFAULT 0,   -- 0 or 1
    paragraph_done  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, date)
);
"""

_CREATE_SUBMISSIONS = """
CREATE TABLE IF NOT EXISTS submissions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    word_id      INTEGER,
    type         TEXT    NOT NULL,   -- 'sentence' | 'story' | 'paragraph'
    text         TEXT    NOT NULL,
    submitted_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

_CREATE_USER_SETTINGS = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id       INTEGER PRIMARY KEY,
    words_per_day INTEGER NOT NULL DEFAULT 12,
    lang          TEXT    NOT NULL DEFAULT 'en',
    reminder_time TEXT    NOT NULL DEFAULT '08:00',
    cluster_mode  INTEGER NOT NULL DEFAULT 0,   -- 0=off, 1=on
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

_CREATE_QUIZ_STATE = """
CREATE TABLE IF NOT EXISTS quiz_state (
    user_id       INTEGER PRIMARY KEY,
    word_ids      TEXT    NOT NULL DEFAULT '[]',  -- JSON list of word IDs in queue
    current_index INTEGER NOT NULL DEFAULT 0,
    direction     TEXT    NOT NULL DEFAULT 'en_to_fr',
    session_type  TEXT    NOT NULL DEFAULT 'review',  -- 'review' | 'new'
    correct       INTEGER NOT NULL DEFAULT 0,
    total         INTEGER NOT NULL DEFAULT 0,
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

_ALL_TABLES = [
    _CREATE_WORDS,
    _CREATE_USER_PROGRESS,
    _CREATE_DAILY_SCHEDULE,
    _CREATE_SUBMISSIONS,
    _CREATE_USER_SETTINGS,
    _CREATE_QUIZ_STATE,
]


async def init_db(db_path: Path) -> None:
    """Create all tables if they don't exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        for stmt in _ALL_TABLES:
            await db.execute(stmt)
        await db.commit()
    logger.info("Database initialized at %s", db_path)


async def get_db(db_path: Path) -> aiosqlite.Connection:
    """Open and return an aiosqlite connection with row_factory set."""
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def row_to_dict(row: aiosqlite.Row) -> dict:
    """Convert an aiosqlite Row to a plain dict."""
    return dict(row)


def parse_collocations(raw: str | list | None) -> list[str]:
    """Safely parse collocations field (JSON string or list)."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
