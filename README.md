# french5000

Structured French learning assets based on Lonsdale, D., Le Bras, Y. A. — A Frequency Dictionary of French (2009).

## Repository layout

```text
.
├── data/
│   ├── raw/                 # source PDF (gitignored)
│   ├── interim/             # intermediate extraction artifacts
│   └── processed/           # final JSON datasets
├── docs/                    # extraction instructions and task notes
├── apps/
│   ├── french-vocab-bot/    # Telegram bot application
│   └── french-vocab-mobile/ # Android app (Capacitor)
├── tools/
│   └── extraction/          # reusable extraction/enrichment scripts
├── .gitignore
└── README.md
```

## Datasets

- `data/interim/french_frequency.json`: raw frequency extraction from the PDF.
- `data/processed/french_frequency_dictionary.json`: enriched frequency dictionary.
- `data/processed/french_thematic_vocabulary.json`: thematic vocabulary lists with rank cross-links.

## Mobile app (Android)

The Android app lives in `apps/french-vocab-mobile/` and is built with Capacitor 8 (WebView wrapper).

**Features:**
- Spaced repetition (1→3→7→14→30→60 day intervals)
- 27 thematic vocabulary categories
- EN→FR reverse mode (English prompt, reveal French)
- Daily reminder notifications
- Search across all 5000 words
- Paris background UI

**Run locally (browser):**
```bash
cd apps/french-vocab-mobile
npm run dev          # serves on http://localhost:3000
```

**Build APK (debug):**
```bash
cd apps/french-vocab-mobile
JAVA_HOME="..." npx cap sync android
cd android && ./gradlew assembleDebug
# Output: android/app/build/outputs/apk/debug/french5000-v1.0-debug.apk
```

**Build AAB (Google Play release):**
```bash
cd apps/french-vocab-mobile
JAVA_HOME="..." npx cap sync android
cd android && ./gradlew bundleRelease
# Output: android/app/build/outputs/bundle/release/app-release.aab
```

> **Important:** The signing keystore (`android/app/french5000.keystore`) is gitignored. Keep it safe — losing it means you cannot publish updates.

## Bot application

The Telegram bot lives in `apps/french-vocab-bot/` and uses:

- `db/app.db` for SQLite storage.
- `data/processed/french_frequency_dictionary.json` as the default import source.

Create `apps/french-vocab-bot/.env` from `.env.example`, then run the bot from `apps/french-vocab-bot/`.

## Extraction tools

All extraction utilities are in `tools/extraction/`:

- `pdf2json.py`: raw frequency extraction from the source PDF.
- `enrich.py`: one-shot enrichment pipeline.
- `enrich_resumable.py`: resumable enrichment pipeline.
- `fill_missing_ru.py`: backfill Russian translations in parallel.
- `extract_thematic_vocab.py`: thematic vocabulary extraction.

These scripts now use repository-relative paths and expect the source PDF at:

- `data/raw/Lonsdale D., Le Bras Y. A. - Frequency Dictionary of French - 2009.pdf`

## Notes

- The source PDF is intentionally gitignored.
- Runtime checkpoints and intermediate resumable artifacts are gitignored.
- Final processed datasets are tracked.
