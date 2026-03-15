"""Writing handlers: /sentences, /story, /paragraph, /listen."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from bot.services.progress import (
    add_submission,
    get_or_create_daily,
    get_user_settings,
    increment_daily,
    set_daily_flag,
)
from bot.services.vocabulary import get_recent_words, get_today_new_words
from bot.utils.config import DB_PATH, WORDS_PER_DAY
from bot.utils.formatter import (
    format_sentence_prompt,
    format_story_prompt,
    format_weekly_paragraph_prompt,
)

logger = logging.getLogger(__name__)

# State keys
STATE_SENTENCE = "sentence_state"   # values: 'waiting_1', 'waiting_2'
STATE_STORY = "story_state"         # value: 'waiting'
STATE_PARAGRAPH = "paragraph_state" # value: 'waiting'


# ── /sentences ────────────────────────────────────────────────────────────────

async def cmd_sentences(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    wpd = settings.get("words_per_day", WORDS_PER_DAY)

    daily = await get_or_create_daily(user_id)
    done = daily.get("sentences_done", 0)
    if done >= 2:
        await update.effective_message.reply_text(
            "✅ You've already completed today's sentence task!\n"
            "Use /story for the micro-story, or /today to see your plan."
        )
        return

    words = await get_today_new_words(user_id, wpd)
    if not words:
        words = await get_recent_words(user_id, days=7)

    msg = format_sentence_prompt(words)
    await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)

    # Set state
    context.user_data[STATE_SENTENCE] = "waiting_1" if done == 0 else "waiting_2"
    context.user_data["sentence_words"] = [w["id"] for w in words[:6]]


# ── /story ────────────────────────────────────────────────────────────────────

async def cmd_story(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    wpd = settings.get("words_per_day", WORDS_PER_DAY)

    daily = await get_or_create_daily(user_id)
    if daily.get("story_done", 0):
        await update.effective_message.reply_text(
            "✅ You've already completed today's micro-story!\n"
            "Use /today to see your full plan."
        )
        return

    words = await get_today_new_words(user_id, wpd)
    if not words:
        words = await get_recent_words(user_id, days=7)

    msg = format_story_prompt(words[:5])
    await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)

    context.user_data[STATE_STORY] = "waiting"
    context.user_data["story_words"] = [w["id"] for w in words[:5]]


# ── /paragraph ────────────────────────────────────────────────────────────────

async def cmd_paragraph(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    daily = await get_or_create_daily(user_id)
    if daily.get("paragraph_done", 0):
        await update.effective_message.reply_text(
            "✅ You've already submitted this week's paragraph!\n"
            "Great work. See you next week."
        )
        return

    words = await get_recent_words(user_id, days=7)
    if not words:
        await update.effective_message.reply_text(
            "No recent words found. Learn some words first with /new!"
        )
        return

    msg = format_weekly_paragraph_prompt(words)
    await update.effective_message.reply_text(msg, parse_mode=ParseMode.HTML)
    context.user_data[STATE_PARAGRAPH] = "waiting"


# ── /listen ───────────────────────────────────────────────────────────────────

async def cmd_listen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    recent = await get_recent_words(user_id, days=7)
    word_list = ", ".join(
        f"<b>{w['word']}</b>" for w in recent[:8]
    ) if recent else "your recent vocabulary"

    await update.effective_message.reply_text(
        "🎧 <b>Weekly Listening Task</b>\n\n"
        "This week's listening challenge:\n\n"
        "1. Visit <a href='https://www.rfi.fr/fr/podcasts/journal-en-français-facile'>RFI Journal en français facile</a>\n"
        "2. Listen to a recent episode (5–7 minutes)\n"
        "3. Try to identify these words from your recent lessons:\n"
        f"   {word_list}\n\n"
        "4. Write one sentence about what you heard (reply to this message).\n\n"
        "No audio file yet — this will be added in a future update. 🔜",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# ── Universal text message handler for writing tasks ─────────────────────────

async def handle_text_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Route incoming text messages to the active writing task state.
    Only fires when a writing task is active (state key set in user_data).
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check which state is active
    if STATE_SENTENCE in context.user_data:
        state = context.user_data[STATE_SENTENCE]
        await _handle_sentence_input(update, context, user_id, text, state)

    elif STATE_STORY in context.user_data:
        await _handle_story_input(update, context, user_id, text)

    elif STATE_PARAGRAPH in context.user_data:
        await _handle_paragraph_input(update, context, user_id, text)

    # If no active writing state, fall through (other handlers may catch it)


async def _handle_sentence_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    text: str,
    state: str,
) -> None:
    word_ids = context.user_data.get("sentence_words", [])
    word_id = word_ids[0] if word_ids else None

    await add_submission(user_id, text, "sentence", word_id)
    await increment_daily(user_id, "sentences_done")

    if state == "waiting_1":
        context.user_data[STATE_SENTENCE] = "waiting_2"
        await update.message.reply_text(
            "✅ Sentence 1 saved!\n\n"
            "Now write your 2nd sentence using a different word from today."
        )
    else:
        # Done
        del context.user_data[STATE_SENTENCE]
        context.user_data.pop("sentence_words", None)
        await update.message.reply_text(
            "✅ Both sentences saved! Well done.\n\n"
            "Use /story for today's micro-story, or /today to see your plan."
        )


async def _handle_story_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    text: str,
) -> None:
    word_ids = context.user_data.get("story_words", [])
    word_id = word_ids[0] if word_ids else None

    await add_submission(user_id, text, "story", word_id)
    await set_daily_flag(user_id, "story_done", 1)

    del context.user_data[STATE_STORY]
    context.user_data.pop("story_words", None)

    await update.message.reply_text(
        "✅ Micro-story saved! Excellent work.\n\n"
        "Use /today to see your full daily plan."
    )


async def _handle_paragraph_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    text: str,
) -> None:
    if len(text.split()) < 20:
        await update.message.reply_text(
            "Your paragraph seems too short. Aim for 80–120 words.\n"
            "Keep writing — you can do it! 💪"
        )
        return

    await add_submission(user_id, text, "paragraph")
    await set_daily_flag(user_id, "paragraph_done", 1)

    del context.user_data[STATE_PARAGRAPH]

    await update.message.reply_text(
        "✅ Weekly paragraph saved! Great effort.\n\n"
        "Use /stats to see your weekly progress."
    )


def register_writing_handlers(app) -> None:
    app.add_handler(CommandHandler("sentences", cmd_sentences))
    app.add_handler(CommandHandler("story", cmd_story))
    app.add_handler(CommandHandler("paragraph", cmd_paragraph))
    app.add_handler(CommandHandler("listen", cmd_listen))

    # Text handler for writing submissions — lower group number = higher priority
    # Group 10 so it runs after command handlers (group 0)
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_submission,
        ),
        group=10,
    )
