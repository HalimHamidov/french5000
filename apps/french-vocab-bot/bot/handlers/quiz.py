"""Interactive quiz callbacks — multiple choice and SRS rating."""
from __future__ import annotations

import logging
import random
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, ContextTypes

from bot.services.progress import increment_daily
from bot.services.srs import (
    QUALITY_AGAIN,
    QUALITY_EASY,
    QUALITY_GOOD,
    QUALITY_HARD,
    record_review,
)
from bot.services.vocabulary import get_random_distractors, get_word_by_id, get_words_by_ids
from bot.utils.config import QUIZ_CHOICES
from bot.utils.formatter import format_quiz_question, format_word_card

logger = logging.getLogger(__name__)


# ── Build a quiz card ─────────────────────────────────────────────────────────

async def send_quiz_card(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    word: dict[str, Any],
    session_type: str = "review",
) -> None:
    """Send a multiple-choice quiz question for `word`."""
    direction = random.choice(["en_to_fr", "fr_to_en"])
    distractors = await get_random_distractors(word, count=QUIZ_CHOICES - 1)

    if direction == "en_to_fr":
        correct_answer = word.get("word", "")
        choices = [correct_answer] + [d.get("word", "") for d in distractors]
    else:
        correct_answer = word.get("translation_en", "")
        choices = [correct_answer] + [d.get("translation_en", "") for d in distractors]

    # Remove duplicates, shuffle
    seen = set()
    unique_choices = []
    for c in choices:
        if c and c not in seen:
            seen.add(c)
            unique_choices.append(c)
    while len(unique_choices) < 2:
        unique_choices.append("?")
    random.shuffle(unique_choices)

    question_text = format_quiz_question(word, unique_choices, direction)

    # Store quiz state
    context.user_data["quiz_word_id"] = word["id"]
    context.user_data["quiz_correct_answer"] = correct_answer
    context.user_data["quiz_direction"] = direction
    context.user_data["quiz_session_type"] = session_type

    # Build choice buttons — encode answer index in callback
    buttons = []
    for i, choice in enumerate(unique_choices):
        buttons.append(
            InlineKeyboardButton(choice, callback_data=f"quiz_ans:{i}:{choice}")
        )
    # Arrange in 2-column grid
    rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    keyboard = InlineKeyboardMarkup(rows)

    await update.effective_message.reply_text(
        question_text, parse_mode=ParseMode.HTML, reply_markup=keyboard
    )


# ── Handle answer choice ──────────────────────────────────────────────────────

async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called when user taps a multiple-choice answer button."""
    query = update.callback_query
    await query.answer()

    data = query.data  # "quiz_ans:0:répondre"
    parts = data.split(":", 2)
    chosen_answer = parts[2] if len(parts) > 2 else ""

    word_id = context.user_data.get("quiz_word_id")
    correct_answer = context.user_data.get("quiz_correct_answer", "")
    direction = context.user_data.get("quiz_direction", "en_to_fr")
    session_type = context.user_data.get("quiz_session_type", "review")
    user_id = update.effective_user.id

    is_correct = chosen_answer.strip().lower() == correct_answer.strip().lower()

    word = await get_word_by_id(word_id) if word_id else None
    word_display = format_word_card(word) if word else f"Word #{word_id}"

    if is_correct:
        result_text = (
            f"✅ <b>Correct!</b>\n\n"
            f"{word_display}\n\n"
            "Rate how easy it was:"
        )
    else:
        result_text = (
            f"❌ <b>Incorrect.</b> The answer was: <b>{correct_answer}</b>\n\n"
            f"{word_display}\n\n"
            "Rate this card:"
        )

    # SRS rating buttons
    rating_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 Again", callback_data=f"srs:{word_id}:{QUALITY_AGAIN}"),
            InlineKeyboardButton("🟡 Hard", callback_data=f"srs:{word_id}:{QUALITY_HARD}"),
            InlineKeyboardButton("🟢 Good", callback_data=f"srs:{word_id}:{QUALITY_GOOD}"),
            InlineKeyboardButton("⭐ Easy", callback_data=f"srs:{word_id}:{QUALITY_EASY}"),
        ]
    ])

    await query.edit_message_text(
        result_text, parse_mode=ParseMode.HTML, reply_markup=rating_keyboard
    )


# ── Handle SRS rating ─────────────────────────────────────────────────────────

async def handle_srs_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called when user taps Again/Hard/Good/Easy after seeing answer."""
    query = update.callback_query
    await query.answer()

    data = query.data  # "srs:42:2"
    _, word_id_str, quality_str = data.split(":")
    word_id = int(word_id_str)
    quality = int(quality_str)
    user_id = update.effective_user.id
    session_type = context.user_data.get("quiz_session_type", "review")

    await record_review(user_id, word_id, quality)
    await increment_daily(user_id, "reviews_done")

    quality_labels = {0: "Again 🔴", 1: "Hard 🟡", 2: "Good 🟢", 3: "Easy ⭐"}
    label = quality_labels.get(quality, str(quality))

    # Advance to next word in queue
    review_queue = context.user_data.get("review_queue", [])
    review_index = context.user_data.get("review_index", 0) + 1
    context.user_data["review_index"] = review_index

    correct = context.user_data.get("review_correct", 0)
    if quality >= QUALITY_GOOD:
        correct += 1
        context.user_data["review_correct"] = correct

    total = context.user_data.get("review_total", len(review_queue))

    if review_index < len(review_queue):
        next_word_id = review_queue[review_index]
        next_word = await get_word_by_id(next_word_id)
        if next_word:
            await query.edit_message_text(
                f"Rated: {label}  ({review_index}/{total})",
                parse_mode=ParseMode.HTML,
            )
            await send_quiz_card(update, context, next_word, session_type)
        else:
            await query.edit_message_text(f"Rated: {label}. Word not found, skipping.")
    else:
        # Session complete
        await query.edit_message_text(
            f"🎉 <b>Review session complete!</b>\n\n"
            f"Answered: {total} cards\n"
            f"Rated Good or Easy: {correct}/{total}\n\n"
            "Use /today to see remaining tasks.",
            parse_mode=ParseMode.HTML,
        )
        # Clean up
        for key in ("review_queue", "review_index", "review_correct", "review_total",
                    "quiz_word_id", "quiz_correct_answer", "quiz_direction", "quiz_session_type"):
            context.user_data.pop(key, None)


# ── Register ──────────────────────────────────────────────────────────────────

def register_quiz_handlers(app) -> None:
    app.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern=r"^quiz_ans:"))
    app.add_handler(CallbackQueryHandler(handle_srs_rating, pattern=r"^srs:"))
