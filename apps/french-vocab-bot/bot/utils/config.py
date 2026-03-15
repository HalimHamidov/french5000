"""Configuration loader — reads .env and exposes typed settings."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Locate app and repository roots
APP_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = APP_ROOT.parent.parent

# Load .env from app root if it exists
_env_file = APP_ROOT / ".env"
load_dotenv(dotenv_path=_env_file, override=False)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(
            f"Environment variable '{key}' is not set. "
            f"Copy .env.example to .env and fill in the values."
        )
    return value


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _resolve_path(root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return root / path


# --- Required ---
BOT_TOKEN: str = _require("BOT_TOKEN")
ADMIN_CHAT_ID: int = int(_require("ADMIN_CHAT_ID"))

# --- Optional with defaults ---
DB_PATH: Path = _resolve_path(APP_ROOT, _get("DB_PATH", "db/app.db"))
DATA_PATH: Path = _resolve_path(REPO_ROOT, _get("DATA_PATH", "data/processed/french_frequency_dictionary.json"))

TIMEZONE: str = _get("TIMEZONE", "UTC")
WORDS_PER_DAY: int = int(_get("WORDS_PER_DAY", "12"))

MORNING_REVIEW_TIME: str = _get("MORNING_REVIEW_TIME", "08:00")
AFTERNOON_LESSON_TIME: str = _get("AFTERNOON_LESSON_TIME", "14:00")
EVENING_REMINDER_TIME: str = _get("EVENING_REMINDER_TIME", "20:00")
WEEKLY_SUMMARY_DAY: str = _get("WEEKLY_SUMMARY_DAY", "sunday").lower()

# SRS intervals in days
SRS_INTERVALS: list[int] = [0, 1, 3, 7, 16, 35, 60]

# Quiz: number of multiple-choice options
QUIZ_CHOICES: int = 4
