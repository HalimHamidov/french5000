import re
import json
import sys
from pathlib import Path
import PyPDF2

sys.stdout.reconfigure(encoding='utf-8')

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = REPO_ROOT / 'data' / 'raw' / 'Lonsdale D., Le Bras Y. A. - Frequency Dictionary of French - 2009.pdf'
OUTPUT_PATH = REPO_ROOT / 'data' / 'interim' / 'french_frequency.json'

# All known POS tokens (with optional gender/number markers)
POS_TOKEN = r'(?:nadj|adj|adv|conj|det|intj|nfm|nmf|nf|nmi|nm|prep|pro|v|art|num|excl|pfx|sfx|adji|interj|pron|nmp|nfp|nmpl|nfpl)(?:\((?:f|m|pl|fpl|mpl)\))?'
POS_RE = re.compile(rf'^({POS_TOKEN}(?:\s*,\s*{POS_TOKEN})*)$')

# Entry line: RANK WORD POS... TRANSLATION
# Allow 0-2 leading junk chars (register code digit or replacement char merged from prev line)
ENTRY_RE = re.compile(
    rf'^.{{0,2}}?(\d{{1,5}})\s+(\S+)\s+({POS_TOKEN}(?:\s*,\s*{POS_TOKEN})*)\s+(.+)$'
)
# Fallback: entries where POS is absent (e.g. "404 afin in order to")
# or word contains apostrophe/hyphen/space (e.g. "596 d'après according to")
# Restrict: word must be lowercase French chars only, translation must be short plain English
ENTRY_NPOS_RE = re.compile(
    r'^.{0,2}?(\d{1,5})\s+([a-zàâäéèêëîïôùûüÿœæç\'\-]+(?:\s[a-zàâäéèêëîïôùûüÿœæç\'\-]+)?)\s+([a-z][a-zA-Z ,;\-\'\.]{3,60})$'
)

EXAMPLE_RE = re.compile(r'^\*\s*(.+?)\s+--\s+(.+?)(?:\s+(\d{{1,3}})\s*\|\s*(\d+).*)?$')
STATS_RE = re.compile(r'^(\d{1,3})\s*\|\s*(\d+)')

def clean(t):
    t = re.sub(r'<[^>]+>', '', t)
    return t.strip()

def extract_pages(path):
    reader = PyPDF2.PdfReader(path)
    return [page.extract_text() or '' for page in reader.pages]

def parse(pages):
    entries = []
    lines = []
    for page_text in pages:
        for line in page_text.split('\n'):
            line = line.strip()
            if line:
                lines.append(line)

    i = 0
    current = None

    while i < len(lines):
        line = lines[i]

        m = ENTRY_RE.match(line) or (not line.startswith('*') and ENTRY_NPOS_RE.match(line))
        if m:
            rank = int(m.group(1))
            # If rank > 5000, it may have a register digit prepended (e.g. "7120" = reg 7 + rank 120)
            if rank > 5000:
                s = m.group(1)
                for strip in range(1, 3):
                    candidate = int(s[strip:]) if len(s) > strip else 0
                    if 1 <= candidate <= 5000:
                        rank = candidate
                        break
                else:
                    i += 1
                    continue
            if 1 <= rank <= 5000:
                if current:
                    entries.append(current)
                # ENTRY_RE has 4 groups; ENTRY_NPOS_RE has 3 (no POS group)
                if m.lastindex == 4:
                    pos = re.sub(r'\s*,\s*', ',', m.group(3))
                    translation = clean(m.group(4))
                else:
                    pos = None
                    translation = clean(m.group(3))
                current = {
                    'id': rank,
                    'rank': rank,
                    'word': m.group(2),
                    'pos': pos,
                    'translation_en': translation,
                    'example_fr': None,
                    'example_en': None,
                    'dispersion': None,
                    'frequency': None,
                    'semantic_cluster': None,
                    'collocations': [],
                    'audio': None,
                    'notes': None,
                }
                i += 1
                continue

        if current:
            # Example line (may also contain stats at the end)
            if line.startswith('*'):
                # Remove leading *
                content = line[1:].strip()
                # Check if stats are embedded at end of line
                stats_embedded = re.search(r'\s+(\d{1,3})\s*\|\s*(\d+)', content)
                if stats_embedded:
                    current['dispersion'] = int(stats_embedded.group(1))
                    current['frequency'] = int(stats_embedded.group(2))
                    content = content[:stats_embedded.start()].strip()
                # Split on --
                if ' -- ' in content:
                    parts = content.split(' -- ', 1)
                    current['example_fr'] = parts[0].strip()
                    current['example_en'] = clean(parts[1].strip())
                elif ' -' in content:
                    parts = content.split(' -', 1)
                    current['example_fr'] = parts[0].strip()
                i += 1
                continue

            # Stats line
            st = STATS_RE.match(line)
            if st and current['dispersion'] is None:
                current['dispersion'] = int(st.group(1))
                current['frequency'] = int(st.group(2))
                i += 1
                continue

            # Stats embedded in a non-* line (e.g. translation wraps and stat follows)
            if current['example_en'] and current['dispersion'] is None:
                st2 = re.search(r'(\d{1,3})\s*\|\s*(\d+)', line)
                if st2:
                    current['dispersion'] = int(st2.group(1))
                    current['frequency'] = int(st2.group(2))
                    i += 1
                    continue

        i += 1

    if current:
        entries.append(current)

    return entries

def main():
    print('Reading PDF...')
    pages = extract_pages(PDF_PATH)
    print(f'Extracted {len(pages)} pages')

    print('Parsing entries...')
    entries = parse(pages)

    # Deduplicate keeping first occurrence
    seen = {}
    for e in entries:
        if e['rank'] not in seen:
            seen[e['rank']] = e

    unique = sorted(seen.values(), key=lambda x: x['rank'])
    print(f'Unique entries (rank 1-5000): {len(unique)}')

    ranks = [e['rank'] for e in unique]
    missing = [r for r in range(1, 5001) if r not in set(ranks)]
    print(f'Missing ranks: {len(missing)}')
    if missing:
        print(f'First 30 missing: {missing[:30]}')

    with_ex = sum(1 for e in unique if e['example_fr'])
    print(f'Entries with example: {with_ex}/{len(unique)}')

    print('\nSample (first 5):')
    for e in unique[:5]:
        print(f'  {e["rank"]}. {e["word"]} ({e["pos"]}) = {e["translation_en"]}')

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    print(f'\nSaved {len(unique)} entries → {OUTPUT_PATH}')

if __name__ == '__main__':
    main()
