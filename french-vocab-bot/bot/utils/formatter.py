"""Message formatting helpers for the French vocabulary bot."""
import json
from datetime import date, timedelta
from typing import Any


def format_word_card(word: dict[str, Any]) -> str:
    """
    Format a single word entry as a Telegram message.

    Example output:
        #144 | question | nf
        📖 question
        🇬🇧 question
        ✏️ je suis gêné de répondre à cette question
           I'm embarrassed to answer this question
        🔗 poser une question, une question de...
    """
    rank = word.get("rank", "?")
    w = word.get("word", "")
    pos = word.get("pos", "")
    translation = word.get("translation_en", "")
    example_fr = word.get("example_fr", "")
    example_en = word.get("example_en", "")
    cluster = word.get("semantic_cluster") or ""
    notes = word.get("notes") or ""

    # Collocations may be stored as JSON string or list
    raw_collocations = word.get("collocations") or []
    if isinstance(raw_collocations, str):
        try:
            raw_collocations = json.loads(raw_collocations)
        except (json.JSONDecodeError, TypeError):
            raw_collocations = []
    collocations: list[str] = raw_collocations if isinstance(raw_collocations, list) else []

    lines = [f"#{rank} | {w} | {pos}"]
    lines.append(f"📖 {w}")
    lines.append(f"🇬🇧 {translation}")

    if example_fr:
        lines.append(f"✏️ {example_fr}")
        if example_en:
            lines.append(f"   {example_en}")

    if collocations:
        lines.append(f"🔗 {', '.join(collocations)}")

    if cluster:
        lines.append(f"🏷 {cluster}")

    if notes:
        lines.append(f"💡 {notes}")

    return "\n".join(lines)


def format_word_list(words: list[dict[str, Any]]) -> str:
    """Format a list of words separated by dividers."""
    cards = [format_word_card(w) for w in words]
    return "\n\n──────────────\n\n".join(cards)


def format_review_prompt(word: dict[str, Any], direction: str = "en_to_fr") -> str:
    """
    Format a review card prompt.
    direction: 'en_to_fr' | 'fr_to_en'
    """
    w = word.get("word", "")
    translation = word.get("translation_en", "")

    if direction == "en_to_fr":
        return f"🔍 Translate to French:\n\n<b>{translation}</b>"
    else:
        return f"🔍 What does this mean?\n\n<b>{w}</b>"


def format_today_plan(
    new_count: int,
    review_count: int,
    sentences_done: int,
    story_done: bool,
    words_per_day: int,
) -> str:
    """Format the /today summary message."""
    new_icon = "✅" if new_count >= words_per_day else f"({new_count}/{words_per_day})"
    review_icon = "✅" if review_count == 0 else f"📋 {review_count} due"
    sent_icon = "✅" if sentences_done >= 2 else f"({sentences_done}/2)"
    story_icon = "✅" if story_done else "⏳"

    lines = [
        "📅 <b>Today's Learning Plan</b>",
        "",
        f"📚 New words: {new_icon}",
        f"🔁 Reviews: {review_icon}",
        f"✏️ Sentences: {sent_icon}",
        f"📝 Micro-story: {story_icon}",
        "",
        "Use /new, /review, /sentences, /story to start each task.",
    ]
    return "\n".join(lines)


def format_stats(stats: dict[str, Any]) -> str:
    """Format the /stats response."""
    lines = [
        "📊 <b>Your Progress</b>",
        "",
        f"📖 Words learned: {stats.get('total_words', 0)}",
        f"🔁 Total reviews: {stats.get('total_reviews', 0)}",
        f"🔥 Current streak: {stats.get('streak', 0)} days",
        f"✅ Words mastered (≥5 reviews): {stats.get('mastered', 0)}",
        f"📅 Active since: {stats.get('since', 'N/A')}",
        "",
        f"This week:",
        f"  New words: {stats.get('week_new', 0)}",
        f"  Reviews: {stats.get('week_reviews', 0)}",
        f"  Sentences written: {stats.get('week_sentences', 0)}",
    ]
    return "\n".join(lines)


def format_morning_notification(review_count: int) -> str:
    if review_count == 0:
        return (
            "🌅 <b>Good morning!</b>\n\n"
            "No reviews due today. Great job keeping up!\n\n"
            "Use /new to learn today's new words."
        )
    minutes = max(5, review_count * 20 // 60 + 1)
    return (
        f"🌅 <b>Good morning!</b>\n\n"
        f"You have <b>{review_count} word(s)</b> to review today.\n"
        f"Estimated time: ~{minutes} minutes.\n\n"
        f"Use /review to start your review session."
    )


def format_evening_reminder(
    new_done: bool, review_count: int, sentences_done: int, story_done: bool
) -> str:
    pending = []
    if not new_done:
        pending.append("📚 New words (/new)")
    if review_count > 0:
        pending.append(f"🔁 {review_count} reviews (/review)")
    if sentences_done < 2:
        pending.append(f"✏️ Sentences ({sentences_done}/2) (/sentences)")
    if not story_done:
        pending.append("📝 Micro-story (/story)")

    if not pending:
        return "🌙 Great work today! All tasks complete. See you tomorrow! 🎉"

    task_list = "\n".join(f"  • {t}" for t in pending)
    return (
        f"🌙 <b>Evening reminder</b>\n\n"
        f"You still have tasks pending:\n{task_list}\n\n"
        f"Even 5 minutes now will help your retention!"
    )


def format_sentence_prompt(words: list[dict[str, Any]]) -> str:
    """Format the daily sentence writing prompt."""
    word_list = ", ".join(
        f"<b>{w['word']}</b> ({w.get('translation_en', '')})" for w in words[:6]
    )
    return (
        "✏️ <b>Sentence Practice</b>\n\n"
        f"Write 2 sentences using any words from today's lesson.\n\n"
        f"Today's words include: {word_list}\n\n"
        "Just type your sentence(s) and I'll save them.\n"
        "Type /skip to skip this task."
    )


def format_story_prompt(words: list[dict[str, Any]]) -> str:
    """Format the daily micro-story prompt."""
    # Pick 3-5 words for the story
    story_words = words[:5]
    word_list = "\n".join(
        f"  • <b>{w['word']}</b> — {w.get('translation_en', '')}" for w in story_words
    )
    return (
        "📝 <b>Micro-story Challenge</b>\n\n"
        "Write a 2–4 sentence story using at least 3 of these words:\n\n"
        f"{word_list}\n\n"
        "Keep it short and natural!\n"
        "Type /skip to skip this task."
    )


def format_weekly_paragraph_prompt(words: list[dict[str, Any]]) -> str:
    """Format the weekly paragraph writing task."""
    word_bank = ", ".join(
        f"<b>{w['word']}</b>" for w in words[:15]
    )
    topics = [
        "a day in Paris",
        "meeting a friend for coffee",
        "your morning routine",
        "a visit to the market",
        "learning something new",
    ]
    import random
    topic = random.choice(topics)
    return (
        "📄 <b>Weekly Paragraph Task</b>\n\n"
        f"Topic: <i>{topic}</i>\n\n"
        f"Word bank (use at least 5):\n{word_bank}\n\n"
        "Write 80–120 words in French. Focus on using vocabulary naturally.\n"
        "Type /skip to skip this task."
    )


def format_cluster_recap(cluster_name: str, words: list[dict[str, Any]]) -> str:
    """Format a semantic cluster recap post."""
    word_lines = "\n".join(
        f"  • <b>{w['word']}</b> ({w.get('pos', '')}) — {w.get('translation_en', '')}"
        for w in words
    )
    return (
        f"🏷 <b>Semantic Cluster: {cluster_name}</b>\n\n"
        f"Here are the words in this group you've seen so far:\n\n"
        f"{word_lines}\n\n"
        "Can you recall a sentence for each one?"
    )


def format_weekly_stats(stats: dict[str, Any]) -> str:
    """Format the weekly progress summary."""
    return (
        "📊 <b>Weekly Summary</b>\n\n"
        f"Words learned this week: <b>{stats.get('week_new', 0)}</b>\n"
        f"Reviews completed: <b>{stats.get('week_reviews', 0)}</b>\n"
        f"Sentences written: <b>{stats.get('week_sentences', 0)}</b>\n"
        f"Stories written: <b>{stats.get('week_stories', 0)}</b>\n"
        f"Streak: <b>{stats.get('streak', 0)} days</b>\n\n"
        f"Total vocabulary: <b>{stats.get('total_words', 0)} words</b>\n"
        f"Words mastered: <b>{stats.get('mastered', 0)}</b>\n\n"
        "Keep it up! Consistency is the key to fluency. 🇫🇷"
    )


def format_quiz_question(word: dict[str, Any], choices: list[str], direction: str) -> str:
    """Format a multiple-choice quiz question."""
    if direction == "en_to_fr":
        prompt = f"How do you say in French:\n\n<b>{word.get('translation_en', '')}</b>"
    else:
        prompt = f"What does this mean?\n\n<b>{word.get('word', '')}</b>"

    return f"❓ {prompt}\n\nChoose the correct answer:"
