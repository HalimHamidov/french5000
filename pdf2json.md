You are given a PDF and  french_frequency.json of the book:

Lonsdale, D., Le Bras, Y. A. — A Frequency Dictionary of French (2009)

Your task is to extract the book into a structured JSON dataset for a Telegram-based French learning bot.

## Goal
Create a JSON file where each entry is one French headword from the book, with clean normalized fields.

The output file must be named:

french_frequency_dictionary.json

## Source-of-truth rules
- Use the PDF as the primary and only source for headwords, rank, examples, and book-derived notes.
- Do NOT invent words, ranks, examples, or collocations not supported by the book.
- If a field is missing in the PDF and cannot be derived safely, set it to null or an empty array depending on the schema.
- Examples must come from the main book, not from your own generation.
- IPA must be provided only for the main French word, not for example sentences.
- Preserve the frequency rank exactly as shown in the book.
- Preserve the main French headword exactly, but normalize obvious OCR issues.
- Output valid UTF-8 JSON.
- Output only machine-usable JSON, no markdown, no commentary.

## Required output schema
Each word entry should look like this:

{
  "id": 124,
  "rank": 124,
  "word": "venir",
  "lemma": "venir",
  "ipa": "/vəniʁ/",
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

## Field-by-field instructions

### id
- Integer.
- Same value as rank unless there is a strong reason to separate them.
- Must be unique.

### rank
- Integer.
- Extract directly from the book’s frequency ranking.

### word
- Main French headword exactly as listed in the book.
- Normalize OCR errors.
- Keep accents.

### lemma
- Usually the same as the headword.
- If the headword is already the lemma, repeat it.
- Do not invent lemmatization beyond obvious normalization.

### ipa
- IPA pronunciation for the main French word only.
- Do not add IPA for examples.
- If IPA is not in the book, derive a standard French IPA carefully from the headword.
- If uncertain, set to null rather than guessing wildly.

### pos
- Part of speech.
- Normalize into short English labels such as:
  - noun
  - verb
  - adjective
  - adverb
  - pronoun
  - preposition
  - conjunction
  - interjection
  - determiner
  - numeral
  - phrase
- If unclear, set to null.

### translation_en
- Main English meaning from the book.
- Keep concise.
- Prefer the most central gloss in the source.

### translation_ru
- Russian translation of the main meaning.
- Translate from the source meaning faithfully.
- Keep concise and learner-friendly.
- Do not over-explain.

### example_fr
- Extract the main example sentence from the book for that entry.
- Must come from the book.
- Preserve French punctuation and accents.
- If no example is present, set to null.

### example_en
- English translation of the example.
- If the book includes it, use the book version.
- If the book gives only French example and not an English translation, translate faithfully into natural English.
- Keep close to the French sentence.

### example_ru
- Russian translation of the same French example.
- Translate faithfully into natural Russian.
- Keep close to the French sentence.

### collocations
- Array of strings.
- Extract collocations, phrase patterns, or common short combinations only if clearly supported by the entry or surrounding source material.
- Do not invent long usage notes.
- If none are clearly extractable, use [].

### semantic_cluster
- Assign a compact semantic category useful for learning.
- Examples:
  - motion verbs
  - family
  - food
  - emotions
  - time
  - places
  - communication
  - work
  - study
  - house
  - quantity
  - common function words
- This may be inferred from meaning, but keep it simple and pedagogically useful.
- Use one main cluster only.

### audio
- Always set to null for now.

### notes
- Short learner-oriented note.
- Only include high-value notes such as:
  - irregular verb
  - common function word
  - false friend risk
  - gender-sensitive noun
  - frequent in spoken French
- Keep notes short.
- If no useful note, set to null.

## Extraction and cleaning rules
- Carefully parse the PDF page by page.
- Fix OCR issues where obvious, especially:
  - broken accents
  - ligature mistakes
  - misread punctuation
  - split words across lines
- Do not merge two separate entries.
- Do not lose ordering.
- Ensure all JSON entries remain in ascending rank order.
- Escape quotes properly.
- Preserve apostrophes correctly in French.
- Preserve Unicode characters such as é, à, ç, œ.

## Translation rules
- English and Russian translations should be concise, accurate, and pedagogically useful.
- Do not make them dictionary essays.
- Prefer one core meaning unless the source clearly lists multiple equally central meanings.
- For Russian, use natural modern Russian.

## Output format requirements
- Produce one JSON array containing all entries.
- Example:

[
  {
    "id": 1,
    "rank": 1,
    "word": "...",
    "lemma": "...",
    "ipa": "...",
    "pos": "...",
    "translation_en": "...",
    "translation_ru": "...",
    "example_fr": "...",
    "example_en": "...",
    "example_ru": "...",
    "collocations": [],
    "semantic_cluster": "...",
    "audio": null,
    "notes": null
  }
]

## Validation requirements
Before saving the final file, validate that:
- JSON is syntactically valid.
- Every entry has all required keys.
- id values are unique.
- rank values are unique and ascending.
- word is non-empty.
- collocations is always an array.
- audio is always null.
- Missing unavailable values are null, not fabricated.
- File encoding is UTF-8.

## Deliverables
Create:
1. french_frequency_dictionary.json
2. extraction_report.md

The report must include:
- total number of extracted entries
- number of entries with missing examples
- number of entries with null ipa
- number of OCR corrections made
- any ambiguous extraction patterns noticed

## Important behavior constraints
- Be conservative.
- Never fabricate source examples.
- Never silently skip malformed entries.
- If an entry is ambiguous, include it with best-effort normalization and mention the issue in extraction_report.md.
- Prioritize correctness and consistency over speed.
In addition to producing the final JSON dataset, write a reusable Python extraction pipeline that:
- reads the PDF
- extracts candidate entries
- normalizes OCR issues
- maps fields into the required schema
- saves french_frequency_dictionary.json
- saves extraction_report.md

Use clear modular Python code with comments and validation checks.
Do not use OCR unless necessary. First try text extraction from the PDF directly.
If OCR is required for some pages, isolate it only to those pages.