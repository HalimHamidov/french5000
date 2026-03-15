"""Learner-facing handlers: /start, /today, /new, /review, /stats, /skip, /help, /cluster."""
from __future__ import annotations

import logging
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from bot.services.progress import (
    ensure_user_settings,
    get_or_create_daily,
    get_user_settings,
    get_user_stats,
    increment_daily,
)
from bot.services.srs import get_due_count, get_due_words, introduce_word
from bot.services.vocabulary import (
    get_all_clusters,
    get_cluster_words,
    get_next_new_words,
    get_today_new_words,
)
from bot.utils.config import DB_PATH, WORDS_PER_DAY
from bot.utils.formatter import (
    format_cluster_recap,
    format_stats,
    format_today_plan,
    format_word_list,
)

logger = logging.getLogger(__name__)


# ── /start ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id

    settings = await ensure_user_settings(user_id)
    wpd = settings.get("words_per_day", WORDS_PER_DAY)

    await update.message.reply_text(
        f"🇫🇷 <b>Bienvenue, {user.first_name}!</b>\n\n"
        "I'm your French vocabulary coach for 2026.\n\n"
        f"Your daily target: <b>{wpd} new words</b> + reviews.\n\n"
        "Commands:\n"
        "/today — see today's plan\n"
        "/new — learn today's new words\n"
        "/review — start review session\n"
        "/sentences — sentence writing task\n"
        "/story — micro-story task\n"
        "/stats — your progress\n"
        "/help — all commands\n\n"
        "Let's get started! Use /today to see what's on for today.",
        parse_mode=ParseMode.HTML,
    )


# ── /help ────────────────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 <b>Available Commands</b>\n\n"
        "<b>Daily learning:</b>\n"
        "/today — today's plan overview\n"
        "/new — learn today's new words\n"
        "/review — review due words\n"
        "/sentences — write 2 sentences\n"
        "/story — write a micro-story\n\n"
        "<b>Weekly:</b>\n"
        "/paragraph — weekly writing task\n"
        "/listen — weekly listening task\n"
        "/cluster — semantic cluster recap\n\n"
        "<b>Progress:</b>\n"
        "/stats — your learning stats\n"
        "/skip — skip current task\n\n"
        "<b>Settings (reply with value):</b>\n"
        "/settings — view/change settings\n",
        parse_mode=ParseMode.HTML,
    )


# ── /today ────────────────────────────────────────────────────────────────────

async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    wpd = settings.get("words_per_day", WORDS_PER_DAY)

    daily = await get_or_create_daily(user_id)
    due_count = await get_due_count(user_id)

    msg = format_today_plan(
        new_count=daily.get("new_words_done", 0),
        review_count=due_count,
        sentences_done=daily.get("sentences_done", 0),
        story_done=bool(daily.get("story_done", 0)),
        words_per_day=wpd,
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📚 New words", callback_data="cmd:new"),
            InlineKeyboardButton("🔁 Review", callback_data="cmd:review"),
        ],
        [
            InlineKeyboardButton("✏️ Sentences", callback_data="cmd:sentences"),
            InlineKeyboardButton("📝 Story", callback_data="cmd:story"),
        ],
    ])
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard)


# ── /new ──────────────────────────────────────────────────────────────────────

async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    wpd = settings.get("words_per_day", WORDS_PER_DAY)

    words = await get_today_new_words(user_id, wpd)
    if not words:
        await update.message.reply_text(
            "🎉 No new words for today! You've learned everything so far.\n"
            "Use /review to practice what you know.",
        )
        return

    # Introduce all words into SRS (idempotent)
    for w in words:
        await introduce_word(user_id, w["id"])

    # Store today's word IDs in context for pagination
    context.user_data["new_words"] = [w["id"] for w in words]
    context.user_data["new_page"] = 0

    await _send_new_words_page(update, context, words, page=0, edit=False)


async def _send_new_words_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    words: list,
    page: int,
    edit: bool = False,
) -> None:
    """Send a page of new words (3 per page) with Next/Done buttons."""
    PAGE_SIZE = 3
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_words = words[start:end]
    total_pages = (len(words) + PAGE_SIZE - 1) // PAGE_SIZE

    text = f"📚 <b>New Words — Page {page + 1}/{total_pages}</b>\n\n"
    text += format_word_list(page_words)

    buttons = []
    if end < len(words):
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"newpage:{page + 1}"))
    else:
        buttons.append(InlineKeyboardButton("✅ Done", callback_data="newpage:done"))

    if page > 0:
        nav = [InlineKeyboardButton("⬅️ Prev", callback_data=f"newpage:{page - 1}")]
        nav.append(buttons[0])
        buttons = nav
    else:
        buttons = [buttons[0]]

    keyboard = InlineKeyboardMarkup([buttons])

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )
    else:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=keyboard
        )


# ── /review ───────────────────────────────────────────────────────────────────

async def cmd_review(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    due_words = await get_due_words(user_id)

    if not due_words:
        await update.message.reply_text(
            "✅ No reviews due right now. Great job!\n\n"
            "Use /new to learn new words or /stats to see your progress."
        )
        return

    # Store review queue in user_data
    context.user_data["review_queue"] = [w["id"] for w in due_words]
    context.user_data["review_index"] = 0
    context.user_data["review_correct"] = 0
    context.user_data["review_total"] = len(due_words)

    await update.message.reply_text(
        f"🔁 <b>Review Session</b>\n\n"
        f"You have <b>{len(due_words)}</b> word(s) to review.\n\n"
        "Answering will update your SRS schedule.\n"
        "Use /skip to end the session early.",
        parse_mode=ParseMode.HTML,
    )

    # Launch quiz via callback
    from bot.handlers.quiz import send_quiz_card
    await send_quiz_card(update, context, due_words[0], session_type="review")


# ── /stats ────────────────────────────────────────────────────────────────────

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    stats = await get_user_stats(user_id)
    msg = format_stats(stats)
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# ── /skip ─────────────────────────────────────────────────────────────────────

async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Clear any active session
    for key in ("review_queue", "review_index", "sentence_state", "story_state",
                "new_words", "new_page", "paragraph_state"):
        context.user_data.pop(key, None)

    await update.message.reply_text(
        "⏭ Task skipped. Use /today to see what's available.",
    )


# ── /cluster ──────────────────────────────────────────────────────────────────

async def cmd_cluster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    clusters = await get_all_clusters()
    if not clusters:
        await update.message.reply_text("No semantic clusters found in the word database yet.")
        return

    import random
    cluster_name = random.choice(clusters)
    words = await get_cluster_words(cluster_name, user_id=user_id, limit=20)

    if not words:
        # Fallback: show cluster without user filter
        words = await get_cluster_words(cluster_name, limit=10)

    if not words:
        await update.message.reply_text(
            f"Cluster '{cluster_name}' has no words yet. Keep learning!"
        )
        return

    msg = format_cluster_recap(cluster_name, words)
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)


# ── /settings ─────────────────────────────────────────────────────────────────

async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)

    wpd = settings.get("words_per_day", 12)
    lang = settings.get("lang", "en")
    reminder = settings.get("reminder_time", "08:00")
    cluster = "on" if settings.get("cluster_mode", 0) else "off"

    await update.message.reply_text(
        "⚙️ <b>Your Settings</b>\n\n"
        f"Words per day: <b>{wpd}</b>\n"
        f"Language: <b>{lang}</b>\n"
        f"Reminder time: <b>{reminder}</b>\n"
        f"Cluster mode: <b>{cluster}</b>\n\n"
        "To change a setting, use:\n"
        "/set_wpd 12  — words per day (12-15)\n"
        "/set_reminder 08:00  — reminder time (HH:MM)\n"
        "/set_cluster on|off  — cluster mode",
        parse_mode=ParseMode.HTML,
    )


async def cmd_set_wpd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /set_wpd <number> (12-15)")
        return
    wpd = int(args[0])
    if not (12 <= wpd <= 15):
        await update.message.reply_text("Words per day must be between 12 and 15.")
        return
    from bot.services.progress import update_user_settings
    await update_user_settings(user_id, {"words_per_day": wpd})
    await update.message.reply_text(f"✅ Words per day set to {wpd}.")


async def cmd_set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /set_reminder HH:MM")
        return
    time_str = args[0]
    try:
        h, m = time_str.split(":")
        assert 0 <= int(h) <= 23 and 0 <= int(m) <= 59
    except Exception:
        await update.message.reply_text("Invalid time format. Use HH:MM, e.g. 08:30")
        return
    from bot.services.progress import update_user_settings
    await update_user_settings(user_id, {"reminder_time": time_str})
    await update.message.reply_text(f"✅ Reminder time set to {time_str}.")


async def cmd_set_cluster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args
    if not args or args[0].lower() not in ("on", "off"):
        await update.message.reply_text("Usage: /set_cluster on|off")
        return
    value = 1 if args[0].lower() == "on" else 0
    from bot.services.progress import update_user_settings
    await update_user_settings(user_id, {"cluster_mode": value})
    await update.message.reply_text(f"✅ Cluster mode {'enabled' if value else 'disabled'}.")


# ── Callback: inline buttons from /today ─────────────────────────────────────

async def handle_cmd_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks that map to commands."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cmd:new":
        await cmd_new(update, context)
    elif data == "cmd:review":
        await cmd_review(update, context)
    elif data == "cmd:sentences":
        from bot.handlers.writing import cmd_sentences
        await cmd_sentences(update, context)
    elif data == "cmd:story":
        from bot.handlers.writing import cmd_story
        await cmd_story(update, context)


# ── Callback: new word pagination ─────────────────────────────────────────────

async def handle_newpage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Next/Prev/Done on the new words paginator."""
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g. "newpage:1" or "newpage:done"

    _, page_str = data.split(":", 1)
    if page_str == "done":
        word_ids = context.user_data.get("new_words", [])
        user_id = update.effective_user.id
        await increment_daily(user_id, "new_words_done", len(word_ids))
        await query.edit_message_text(
            "✅ <b>New words complete!</b>\n\n"
            "Use /review to practice them, or come back later for your reviews.",
            parse_mode=ParseMode.HTML,
        )
        context.user_data.pop("new_words", None)
        context.user_data.pop("new_page", None)
        return

    page = int(page_str)
    context.user_data["new_page"] = page
    word_ids = context.user_data.get("new_words", [])

    from bot.services.vocabulary import get_words_by_ids
    words = await get_words_by_ids(word_ids)
    await _send_new_words_page(update, context, words, page, edit=True)


def register_learner_handlers(app) -> None:
    """Register all learner command handlers with the Application."""
    from telegram.ext import CallbackQueryHandler

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("review", cmd_review))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("skip", cmd_skip))
    app.add_handler(CommandHandler("cluster", cmd_cluster))
    app.add_handler(CommandHandler("settings", cmd_settings))
    app.add_handler(CommandHandler("set_wpd", cmd_set_wpd))
    app.add_handler(CommandHandler("set_reminder", cmd_set_reminder))
    app.add_handler(CommandHandler("set_cluster", cmd_set_cluster))

    app.add_handler(CallbackQueryHandler(handle_cmd_callback, pattern=r"^cmd:"))
    app.add_handler(CallbackQueryHandler(handle_newpage_callback, pattern=r"^newpage:"))
