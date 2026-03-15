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
├── french-vocab-bot/        # Telegram bot application
├── tools/
│   └── extraction/          # reusable extraction/enrichment scripts
├── .gitignore
└── README.md
```

## Datasets

- `data/interim/french_frequency.json`: raw frequency extraction from the PDF.
- `data/processed/french_frequency_dictionary.json`: enriched frequency dictionary.
- `data/processed/french_thematic_vocabulary.json`: thematic vocabulary lists with rank cross-links.

## Bot application

The Telegram bot lives in `french-vocab-bot/` and uses:

- `db/app.db` for SQLite storage.
- `data/processed/french_frequency_dictionary.json` as the default import source.

Create `french-vocab-bot/.env` from `.env.example`, then run the bot from `french-vocab-bot/`.

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
