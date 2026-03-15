"""
enrich.py
---------
Reads french_frequency.json and produces french_frequency_dictionary.json
by adding:
  - lemma     (same as word)
  - ipa       (gruut French phonemizer)
  - translation_ru  (deep-translator, EN→RU)
  - example_ru      (deep-translator, FR→RU)
  - pos       (normalized to schema labels)
  - all other schema fields
"""

import json
import sys
import time
import re
from pathlib import Path
import gruut
from deep_translator import GoogleTranslator

sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = REPO_ROOT / 'data' / 'interim' / 'french_frequency.json'
OUTPUT_PATH = REPO_ROOT / 'data' / 'processed' / 'french_frequency_dictionary.json'

# ---------------------------------------------------------------------------
# POS normalisation
# ---------------------------------------------------------------------------

_POS_MAP = {
    'nm': 'noun', 'nf': 'noun', 'nmi': 'noun', 'nfm': 'noun', 'nmf': 'noun',
    'nmp': 'noun', 'nfp': 'noun', 'nmpl': 'noun', 'nfpl': 'noun', 'nadj': 'adjective',
    'v': 'verb',
    'adj': 'adjective', 'adji': 'adjective',
    'adv': 'adverb',
    'prep': 'preposition',
    'conj': 'conjunction',
    'pro': 'pronoun', 'pron': 'pronoun',
    'intj': 'interjection', 'interj': 'interjection', 'excl': 'interjection',
    'num': 'numeral',
    'pfx': 'phrase', 'sfx': 'phrase',
}

# When an entry has multiple POS tags, pick the first match in this priority order
_POS_PRIORITY = ['v', 'adj', 'nm', 'nf', 'nmi', 'nfm', 'nmf', 'nmp', 'nfp',
                 'nmpl', 'nfpl', 'nadj', 'adv', 'prep', 'det', 'art', 'conj',
                 'pro', 'pron', 'num', 'intj', 'interj', 'excl', 'pfx', 'sfx']


def normalize_pos(pos_str: str | None) -> str | None:
    if not pos_str:
        return None
    parts = [re.split(r'[(]', p)[0].strip() for p in pos_str.split(',')]
    for pref in _POS_PRIORITY:
        if pref in parts:
            return _POS_MAP.get(pref)
    return _POS_MAP.get(parts[0]) if parts else None


# ---------------------------------------------------------------------------
# IPA via gruut
# ---------------------------------------------------------------------------

def get_ipa(word: str) -> str | None:
    """Return IPA string for a single French headword, or None."""
    try:
        # Take only the first word token (handles multiword entries like d'après)
        sents = list(gruut.sentences(word, lang='fr'))
        phones = []
        for sent in sents:
            for w in sent.words:
                if w.is_spoken and w.phonemes:
                    phones.extend(w.phonemes)
        if phones:
            return '/' + ''.join(phones) + '/'
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Batch translation with retry
# ---------------------------------------------------------------------------

def translate_batch(texts: list[str], src: str, dest: str,
                    batch_size: int = 50, delay: float = 1.5) -> list[str | None]:
    """Translate a list of texts in batches. Returns same-length list."""
    results: list[str | None] = []
    translator = GoogleTranslator(source=src, target=dest)
    total = len(texts)

    for start in range(0, total, batch_size):
        chunk = texts[start:start + batch_size]
        # Replace empty strings with a placeholder so translate_batch stays aligned
        safe_chunk = [t if t.strip() else '—' for t in chunk]
        for attempt in range(3):
            try:
                translated = translator.translate_batch(safe_chunk)
                results.extend(t if t and t != '—' else None for t in translated)
                break
            except Exception as e:
                if attempt == 2:
                    print(f'  [WARN] translation failed for batch {start}: {e}')
                    results.extend([None] * len(chunk))
                else:
                    time.sleep(3)
        done = min(start + batch_size, total)
        if done % 500 == 0 or done == total:
            print(f'  {done}/{total}')
        time.sleep(delay)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('Loading french_frequency.json …')
    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    print(f'  Loaded {len(entries)} entries\n')

    # ---- IPA ---------------------------------------------------------------
    print('Generating IPA with gruut …')
    ipa_results = []
    for i, e in enumerate(entries):
        ipa_results.append(get_ipa(e['word']))
        if (i + 1) % 500 == 0:
            print(f'  {i + 1}/{len(entries)}')
    print(f'  Done. IPA found: {sum(1 for x in ipa_results if x)}/{len(entries)}\n')

    # ---- Russian translation of English gloss ------------------------------
    print('Translating translation_en → Russian …')
    en_texts = [e['translation_en'] or '' for e in entries]
    ru_translations = translate_batch(en_texts, src='en', dest='ru')
    print(f'  Done. Got: {sum(1 for x in ru_translations if x)}/{len(entries)}\n')

    # ---- Russian translation of French examples ----------------------------
    print('Translating example_fr → Russian …')
    fr_examples = [e['example_fr'] or '' for e in entries]
    ru_examples = translate_batch(fr_examples, src='fr', dest='ru')
    print(f'  Done. Got: {sum(1 for x in ru_examples if x)}/{len(entries)}\n')

    # ---- Assemble final schema --------------------------------------------
    print('Assembling output …')
    output = []
    for i, e in enumerate(entries):
        ru_t = ru_translations[i] if i < len(ru_translations) else None
        ru_ex = ru_examples[i] if (i < len(ru_examples) and e['example_fr']) else None

        output.append({
            'id':             e['rank'],
            'rank':           e['rank'],
            'word':           e['word'],
            'lemma':          e['word'],
            'ipa':            ipa_results[i],
            'pos':            normalize_pos(e.get('pos')),
            'translation_en': e['translation_en'],
            'translation_ru': ru_t or None,
            'example_fr':     e['example_fr'],
            'example_en':     e['example_en'],
            'example_ru':     ru_ex or None,
            'collocations':   [],
            'semantic_cluster': None,
            'audio':          None,
            'notes':          None,
        })

    # ---- Save --------------------------------------------------------------
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ---- Stats -------------------------------------------------------------
    with_ipa   = sum(1 for e in output if e['ipa'])
    with_ru_t  = sum(1 for e in output if e['translation_ru'])
    with_ru_ex = sum(1 for e in output if e['example_ru'])
    missing_ex = sum(1 for e in output if not e['example_fr'])

    print(f'\nSaved {len(output)} entries → {OUTPUT_PATH}')
    print(f'  IPA populated:          {with_ipa}/{len(output)}')
    print(f'  Russian translation:    {with_ru_t}/{len(output)}')
    print(f'  Russian example:        {with_ru_ex}/{len(output)}')
    print(f'  Missing French example: {missing_ex}/{len(output)}')


if __name__ == '__main__':
    main()
