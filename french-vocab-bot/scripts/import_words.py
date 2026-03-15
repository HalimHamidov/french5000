#!/usr/bin/env python3
"""
import_words.py — Load french_frequency.json into the SQLite database.

Usage:
    python scripts/import_words.py [--data PATH] [--db PATH]

This script reads the JSON file and upserts all words with rank 1–5000
into the `words` table. It is safe to run multiple times (idempotent).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Allow running from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def import_words(data_path: Path, db_path: Path) -> int:
    """Import words from JSON into SQLite. Returns count of upserted rows."""
    from bot.models.database import get_db, init_db

    # Ensure tables exist
    await init_db(db_path)

    logger.info("Reading %s ...", data_path)
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON root must be a list of word objects.")

    logger.info("Total entries in JSON: %d", len(data))

    # Filter to rank 1–5000
    words = [w for w in data if isinstance(w.get("rank"), int) and 1 <= w["rank"] <= 5000]
    logger.info("Words with rank 1–5000: %d", len(words))

    count = 0
    skipped = 0

    async with await get_db(db_path) as db:
        for item in words:
            try:
                rank = item["rank"]
                collocations = item.get("collocations") or []
                if not isinstance(collocations, list):
                    collocations = []
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
            except Exception as exc:
                logger.warning("Skipped rank %s: %s", item.get("rank"), exc)
                skipped += 1

        await db.commit()

    logger.info("Done. Upserted: %d, Skipped: %d", count, skipped)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Import French vocabulary JSON into SQLite.")
    parser.add_argument(
        "--data",
        type=Path,
        default=PROJECT_ROOT / "data" / "french_frequency.json",
        help="Path to french_frequency.json",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=PROJECT_ROOT / "db" / "app.db",
        help="Path to SQLite database file",
    )
    args = parser.parse_args()

    if not args.data.exists():
        logger.error("Data file not found: %s", args.data)
        sys.exit(1)

    count = asyncio.run(import_words(args.data, args.db))
    print(f"\nImport complete: {count} words loaded into {args.db}")


if __name__ == "__main__":
    main()
