# Claude Code Instruction: Build Android Vocab App (French 5000)

Use this as a direct prompt for Claude Code.

## Role

You are a senior Android + frontend engineer. Build a production-ready local-first Android vocabulary app, similar UX/logic to my current "48 Laws Vocab" app https://github.com/HalimHamidov/48laws, but for **French 5000 frequent words**.


## Goal

Create an app for daily memorization with spaced repetition, one-card-at-a-time flow, search over all words, progress stats, reminders, and clean mobile UX.

## Input Data

- Main source file: `french_5000_frequency.json` in project root.
- Must support flexible schema:
  - expected possible fields: `word`, `translation_ru`, `translation_en`, `example`, `meaning`, `ipa`, `rank`, `count`
  - if fields differ, auto-detect best mapping safely.
- Handle malformed rows gracefully: skip invalid items and log warnings.

## Core Product Requirements

1. Show **one word at a time** (no long scroll list of 15 cards).
2. Daily session: exactly `WORDS_PER_DAY` words (default 15).
3. Buttons on word card:
   - `Remove` (exclude forever from learning, still searchable)
   - `Review` (open due review queue)
   - `Next` (schedule next appearance, show approx interval)
4. Previous/Next navigation and counter in center: e.g. `2 / 15`.
5. Swipe gestures:
   - left swipe = next card
   - right swipe = previous card
6. Translation hidden by default with toggle (`Show translation`).
7. IPA hidden by default with toggle (`Show transcription (IPA)`), styled with different font/color.
8. Search over all 5000 words with input + Search + Clear.
9. Compact menu buttons in grid (2-3 columns) to save screen space:
   - Today, Next Batch, Stats, Help
10. Reminder controls compact on one row:
   - `Off` | time picker | `On`
11. No fixed bottom bar that wastes space.
12. Adaptive layout for common Android phone screens (small/medium/large).

## Learning Logic

Use evidence-based principles:
- retrieval practice
- spaced repetition
- low cognitive load
- chunking
- contextual exposure

Implement practical scheduler:
- For new word after successful step: ~1d -> ~3d -> ~7d -> ~14d -> ~30d.
- If user taps Review, place into due queue with shorter interval.
- Avoid immediate repeats in same day unless explicitly reviewing.
- Persist everything locally between app restarts.

## Filtering Rules

Before study queue generation, exclude from learning queue (but keep searchable):
- stopwords/pronouns/articles/prepositions (configurable list),
- single letters/noise tokens,
- proper names (heuristic),
- country names (configurable),
- optionally CEFR A1-B2 words via configurable dictionary list.

Store exclusion reason for stats.

## Stats & Motivation

Stats screen must include:
- learned count,
- excluded count,
- due count,
- percent learned from `(total - excluded)`,
- progress milestones every 100 words,
- stars/emoji achievements every 100 words,
- custom level names (invent progression from beginner to master),
- optional short "moral/proverb" reward every 100 words.

## UX/Style

- Distinct styles/colors for major blocks:
  - header,
  - word card,
  - navigation strip,
  - controls panel.
- NEW and REVIEW badges must be visually distinct.
- Translation text highlighted with separate color.
- Keep buttons stable in position; no jumping when example text is long.
- Ensure UTF-8 rendering works for Russian/French (no `????`).

## Tech Requirements

- Prefer stack already proven in my project:
  - web app in `mobile_app/`
  - optional Capacitor Android wrapper in `android/`
- Keep code modular:
  - data loader,
  - scheduler,
  - state storage,
  - UI rendering,
  - reminders.
- Persist state in local JSON or SQLite (local-only).
- Add logging and graceful error handling.
- Provide `README.md` with setup/build/install instructions.

## Commands / Actions

UI actions required:
- Today
- Next Batch
- Review
- Search
- Clear
- Stats
- Help
- Reset Progress (must be hidden behind confirmation in Help/Settings to avoid accidental tap)

## Deliverables

1. Full source code.
2. `README.md` with run/build instructions.
3. `.env.example` (if configuration used).
4. `requirements.txt` or `package.json` dependencies (matching chosen stack).
5. Brief architecture explanation.
6. Ready debug APK build path in output instructions.

## Output Format Expected From Claude Code

1. First: detected JSON mapping plan.
2. Then: project tree.
3. Then: each created/updated file in separate code block with filename.
4. Then: run steps and APK build steps.
5. Then: short checklist proving each requirement above is covered.

## Constraints

- Do not ask unnecessary questions; make reasonable assumptions.
- Keep implementation directly runnable locally.
- Do not use fake cognitive-science claims.
- Keep UI clean and user-friendly for daily long-term use.
