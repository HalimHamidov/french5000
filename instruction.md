# Telegram Bot Specification for 2026 French Vocabulary Learning

## Goal
Build a Telegram bot that turns a frequency dictionary of French into a full-year learning system for 2026. The bot must not only publish daily vocabulary posts, but also manage review cycles, active recall, sentence production, weekly writing, listening practice, micro-stories, and semantic clustering. The design should maximize long-term retention, not just exposure.

## Core Learning Principles to Implement
The bot must operationalize these mechanisms:

### 1. Spaced repetition
Each word must be reviewed on a schedule after first introduction. Default intervals:
- Day 0
- Day 1
- Day 3
- Day 7
- Day 16
- Day 35
- Day 60 optional for mature words

The bot should track review history for every word and generate daily review queues automatically.

### 2. Retrieval practice
The user should not only see the answer. The bot must regularly ask the user to recall:
- French from English
- English from French
- missing word in a sentence
- meaning from context
- short production prompts

### 3. Contextual learning
Each word should be shown with:
- part of speech
- translation
- one example sentence
- 1 to 3 collocations or phrase patterns
- optionally a semantic group

### 4. Multi-modal learning
The bot should include:
- reading
- listening
- writing
- active recall
- speaking prompt when possible

### 5. Deep encoding
The bot should make the user create:
- 2 sentences daily
- one micro-story using several target words
- one weekly paragraph using recent vocabulary

### 6. Mental map building
Words should also be connected by semantic clusters. Example groups:
- motion verbs
- family
- time
- food
- emotions
- work
- study
- places

The bot should occasionally publish cluster posts and review words by related meaning, not only by raw frequency order.

## Daily Learning Target
The default daily flow must use:
- 12 new words per day
- all due reviews for the day
- 2 sentence-writing prompts
- one short micro-story prompt

Allow configuration for 12 to 15 new words per day, but default to 12 for sustainability.

## Daily Time Budget
The system should aim for 15 to 25 minutes per day total.

Target rhythm:
- morning: review due words
- afternoon or main session: learn 12 new words
- evening: write 2 sentences and complete the micro-story prompt

The bot should handle all three stages inside Telegram.

## Weekly Learning Components
Once per week, the bot must also send:
- one paragraph-writing task using words from the last 7 days
- one listening task with French audio
- one semantic cluster recap
- one weekly progress summary

## Telegram Bot Responsibilities
The bot should behave as a personal French vocabulary coach inside Telegram.

It must support:
1. Daily new-word post
2. Daily review session
3. Interactive quiz prompts
4. Sentence submission by user
5. Micro-story generation task
6. Weekly paragraph task
7. Listening task delivery
8. Progress tracking
9. Admin posting automation
10. Manual override and rescheduling

## User Modes
Support at least two modes:
- learner mode: user receives tasks and answers them
- admin mode: owner manages content, schedules, and publishing

## Data Source
The source will be a JSON dataset created from the frequency dictionary PDF.

Each word entry should ideally contain fields like:

```json
{
  "id": 124,
  "rank": 124,
  "word": "venir",
  "lemma": "venir",
  "pos": "verb",
  "translation_en": "to come",
  "translation_ru": "приходить",
  "example_fr": "Il vient demain.",
  "example_en": "He comes tomorrow.",
  "example_ru": "Он придет завтра.",
  "collocations": ["venir de", "venir chez quelqu'un"],
  "semantic_cluster": "motion verbs",
  "audio": null,
  "notes": "high-frequency irregular verb"
}
```

## Storage Requirements
Use persistent storage for:
- word catalog
- daily schedule
- user progress
- review states
- sentence submissions
- weekly paragraph submissions
- bot settings
- posting history

A simple SQLite database is acceptable for MVP. JSON files can be used for source imports, but user progress should be persisted in a database.

## Scheduling Logic
### New words
Each day the bot selects the next 12 unseen words in frequency order, unless semantic mode is enabled for that day.

### Reviews
Each day the bot calculates all words due for review based on spaced repetition intervals.

### Weekly tasks
On a fixed weekly day, such as Sunday:
- send weekly paragraph challenge
- send listening challenge
- send semantic cluster recap
- send weekly stats

### Missed day handling
If the user skips a day:
- do not flood all missed content at once
- merge backlog gently
- cap total daily burden
- prioritize due reviews and current-day new words

## Bot Commands
Implement commands like these:
- `/start` initialize learner profile
- `/today` show today’s plan
- `/new` show today’s 12 new words
- `/review` start review session
- `/sentences` show today’s sentence task
- `/story` show micro-story task
- `/listen` show weekly listening task
- `/paragraph` show weekly paragraph task
- `/stats` show progress
- `/cluster` show current semantic cluster
- `/skip` skip current task
- `/help` show commands

Admin commands:
- `/admin_schedule`
- `/admin_post_now`
- `/admin_import_json`
- `/admin_set_rate`
- `/admin_reschedule`
- `/admin_broadcast`

## Daily Bot Flow
### 1. Morning review message
The bot sends a review notification with count of due cards.

Example structure:
- number of reviews due
- estimated duration
- quick-start button

### 2. Main lesson message
The bot sends the 12 new words of the day.
For each word include:
- rank
- French word
- part of speech
- translation
- example sentence
- collocation or phrase pattern
- optional semantic note

Words may be sent:
- as one grouped post
- or as a paginated sequence with inline buttons

### 3. Recall practice
After introducing the word set, the bot launches short quizzes:
- translate to French
- choose correct meaning
- fill in blank
- type the missing word

### 4. Sentence production
The bot asks the user to write 2 original sentences using any 2 target words from today.
The bot should accept free text and store it.
Optional AI evaluation can later provide correction or feedback.

### 5. Micro-story prompt
The bot asks the user to create a 2 to 4 sentence micro-story using 3 to 5 words from today’s lesson.
This should be short and realistic.

### 6. Evening reminder
If tasks are incomplete, send a gentle reminder with remaining items.

## Review Session Design
Each review should be interactive.

Supported formats:
- English to French recall
- French to English recall
- sentence completion
- recognition among choices
- typing answer manually

The system should support quality scoring like:
- Again
- Hard
- Good
- Easy

Or simpler for MVP:
- wrong
- correct

Depending on performance, the next review date is adjusted.

## Weekly Workflow
### Weekly paragraph task
Once a week, ask the user to write one paragraph using vocabulary from the last 7 days.
The bot should provide:
- a topic prompt
- a word bank from the week
- a target length, for example 80 to 120 words

### Weekly listening task
Once a week, the bot sends:
- short French audio or external resource
- 3 to 5 comprehension prompts
- optionally words to listen for from the weekly vocabulary

### Weekly semantic cluster recap
The bot sends a cluster review post such as:
- movement verbs
- house vocabulary
- social interaction verbs

This recap should connect previously learned words and build a conceptual map.

### Weekly progress report
The bot sends:
- number of new words learned this week
- number of reviews completed
- streak count
- words mastered
- missed tasks

## Post Formatting Guidelines
### Daily word post format
Each word block should be compact and readable.

Suggested layout:

- Rank number
- French word
- Part of speech
- Translation
- Example sentence in French
- Translation of example
- Collocations
- Tiny challenge

### Review prompt format
Keep prompts short and interactive.
Use buttons where possible.

### Writing prompt format
Sentence and story prompts should be simple and clear.
They should reduce friction so the user actually writes.

## Audio and Listening Layer
The bot should be designed to support audio later even if the first version has no TTS.

Possible sources:
- locally stored pronunciation files
- TTS generation pipeline
- linked French listening materials

For now the architecture should keep an `audio` field per word or lesson item.

## Personalization Options
The bot should support settings such as:
- words per day: 12 to 15
- preferred translation language: English or Russian
- reminder time
- review mode intensity
- semantic cluster mode on or off
- whether to send all words in one message or one by one

## Content Progression Strategy
Primary order:
- frequency rank ascending

Secondary enrichment:
- semantic cluster overlays
- irregular high-value verbs highlighted early
- common function words reinforced often

The bot should not become a dumb word dump. It should build usable command of vocabulary.

## Recommended Architecture
Suggested components:
- Telegram Bot API interface
- scheduler service
- vocabulary engine
- spaced repetition engine
- persistence layer
- admin import pipeline
- optional AI feedback module for writing corrections

## Suggested File Structure
```text
project/
  bot/
    handlers/
    services/
    models/
    utils/
  data/
    french_frequency.json
  db/
    app.db
  scripts/
    import_words.py
    schedule_daily.py
  instruction.md
  README.md
```

## MVP Requirements
The first version must already support:
- loading JSON word dataset
- posting 12 new words daily
- scheduling reviews
- interactive review prompts
- collecting 2 user sentences daily
- collecting one micro-story daily
- one weekly paragraph task
- one weekly listening task placeholder
- progress stats

## Nice-to-Have Features Later
Possible upgrades:
- AI correction of user sentences
- voice pronunciation generation
- auto-generated images for mnemonic stories
- CEFR labeling
- difficulty adaptation
- semantic memory graphs
- export to Anki
- web admin dashboard

## Failure and Edge Cases
Handle these carefully:
- duplicate words in JSON
- missing example sentences
- missing collocations
- user inactivity
- schedule drift
- timezone issues
- accidental double-posting
- malformed JSON import

## UX Principles
The bot should feel:
- lightweight
- encouraging
- consistent
- low-friction
- focused on retention and active use

Avoid huge walls of text in daily posts. The system should be rich in pedagogy but lean in presentation.

## Implementation Notes for Claude Code or Codex
Build the bot as a production-minded MVP with clean modular code.
Use readable abstractions.
Prefer reliability over fancy features.
Make all timings configurable.
Design the data model so that future AI feedback and TTS can be added without breaking the schema.

## Final Product Expectation
The finished bot should function as a daily Telegram-based French learning system for all of 2026, where the learner can:
- learn 12 new words per day
- review old words with spaced repetition
- practice retrieval
- write 2 sentences daily
- build a micro-story daily
- write a weekly paragraph
- do a weekly listening task
- reinforce semantic clusters
- track progress continuously

The bot should turn a frequency dictionary into an active learning machine, not just a posting channel.

