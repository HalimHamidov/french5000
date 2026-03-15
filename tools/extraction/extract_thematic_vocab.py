import json
import re
from pathlib import Path

import fitz
import gruut
from deep_translator import GoogleTranslator


REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = REPO_ROOT / "data" / "raw" / "Lonsdale D., Le Bras Y. A. - Frequency Dictionary of French - 2009.pdf"
FREQ_PATH = REPO_ROOT / "data" / "processed" / "french_frequency_dictionary.json"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "french_thematic_vocabulary.json"


CATEGORIES = [
    {"id": 1, "title": "Animals", "key": "animals", "page": 20, "parser": "standard"},
    {"id": 2, "title": "Body", "key": "body", "page": 35, "parser": "standard"},
    {"id": 3, "title": "Food", "key": "food", "page": 51, "parser": "standard"},
    {"id": 4, "title": "Clothing", "key": "clothing", "page": 67, "parser": "standard"},
    {"id": 5, "title": "Transportation", "key": "transportation", "page": 84, "parser": "standard"},
    {"id": 6, "title": "Family", "key": "family", "page": 100, "parser": "standard"},
    {"id": 7, "title": "Materials", "key": "materials", "page": 116, "parser": "standard"},
    {"id": 8, "title": "Time", "key": "time", "page": 133, "parser": "standard"},
    {"id": 9, "title": "Sports", "key": "sports", "page": 149, "parser": "standard"},
    {"id": 10, "title": "Natural features and plants", "key": "natural_features_and_plants", "page": 166, "parser": "standard"},
    {"id": 11, "title": "Weather", "key": "weather", "page": 182, "parser": "standard"},
    {"id": 12, "title": "Professions", "key": "professions", "page": 198, "parser": "standard"},
    {"id": 13, "title": "Creating nouns – 1", "key": "creating_nouns_1", "page": 214, "parser": "standard"},
    {"id": 14, "title": "Relationships", "key": "relationships", "page": 230, "parser": "standard"},
    {"id": 15, "title": "Nouns – differences across registers", "key": "nouns_differences_across_registers", "page": 246, "parser": "standard"},
    {"id": 16, "title": "Colors", "key": "colors", "page": 263, "parser": "standard"},
    {"id": 17, "title": "Opposites", "key": "opposites", "page": 279, "parser": "opposites"},
    {"id": 18, "title": "Nationalities", "key": "nationalities", "page": 301, "parser": "standard"},
    {"id": 19, "title": "Creating nouns – 2", "key": "creating_nouns_2", "page": 317, "parser": "standard"},
    {"id": 20, "title": "Emotions", "key": "emotions", "page": 333, "parser": "standard"},
    {"id": 21, "title": "Adjectives – differences across registers", "key": "adjectives_differences_across_registers", "page": 349, "parser": "standard"},
    {"id": 22, "title": "Verbs of movement", "key": "verbs_of_movement", "page": 365, "parser": "standard"},
    {"id": 23, "title": "Verbs of communication", "key": "verbs_of_communication", "page": 381, "parser": "standard"},
    {"id": 24, "title": "Use of the pronoun “se”", "key": "use_of_the_pronoun_se", "page": 397, "parser": "se_pronoun"},
    {"id": 25, "title": "Verbs – differences across registers", "key": "verbs_differences_across_registers", "page": 415, "parser": "standard"},
    {"id": 26, "title": "Adverbs – differences across registers", "key": "adverbs_differences_across_registers", "page": 434, "parser": "standard"},
    {"id": 27, "title": "Word length", "key": "word_length", "page": 454, "parser": "word_length"},
]


STANDARD_LINE_RE = re.compile(
    r"^(?P<word>[A-Za-zÀ-ÿŒœÆæ'’\-]+(?:\s+[A-Za-zÀ-ÿŒœÆæ'’\-]+)*)\s+"
    r"(?P<rank>\d{1,5})\s+"
    r"(?:(?P<meta>[A-Za-z()]+)\s+)?"
    r"(?P<gloss>.+)$"
)
MAIN_ENTRY_RE = re.compile(r"^\d{1,5}\s+\S+\s+")
SE_LINE_RE = re.compile(
    r"^(?P<ratio>0(?:\.\d+)?|1(?:\.0+)?)\s+"
    r"(?P<word>[A-Za-zÀ-ÿŒœÆæ'’\-]+(?:\s+[A-Za-zÀ-ÿŒœÆæ'’\-]+)*)\s+"
    r"(?P<rank>\d{1,5})\s+"
    r"(?P<gloss>.+)$"
)

META_TOKENS = {
    "M", "F", "MF", "N", "NM", "NF", "adj", "adv", "nadj", "nm", "nf", "nmi",
    "pro", "conj", "prep", "det", "v", "adji", "n", "nmf", "nfp", "nmp", "nfpl",
    "nmpl", "adjf"
}
SECTION_NOTE_PREFIXES = {
    "Spoken:": "register=spoken",
    "Literature:": "register=literature",
    "Non-fiction:": "register=non-fiction",
    "Positive:": "emotion_group=positive",
    "Neutral:": "emotion_group=neutral",
    "Negative:": "emotion_group=negative",
}


def normalize_title(title):
    return title.replace("–", "--").replace("“", '"').replace("”", '"')


def load_frequency_lookup():
    data = json.load(open(FREQ_PATH, encoding="utf-8"))
    by_word = {item["word"]: item for item in data}
    by_rank = {item["rank"]: item for item in data}
    return by_word, by_rank


def get_ipa(word):
    try:
        phones = []
        for sent in gruut.sentences(word, lang="fr"):
            for token in sent.words:
                if token.is_spoken and token.phonemes:
                    phones.extend(token.phonemes)
        if phones:
            return "/" + "".join(phones) + "/"
    except Exception:
        return None
    return None


def clean_line(line):
    return re.sub(r"\s+", " ", line).strip()


def get_page_text(doc, page_no):
    return doc[page_no - 1].get_text("text")


def extract_segment(text, title, is_start_page):
    working = text.replace("–", "--").replace("“", '"').replace("”", '"')
    if is_start_page:
        idx = working.find(title)
        if idx != -1:
            working = working[idx:]
    lines = [clean_line(line) for line in working.splitlines()]
    return [line for line in lines if line]


def enrich_item(word, translation_en, rank_reference, by_word, by_rank, translator):
    freq = by_word.get(word)
    if not freq and rank_reference is not None:
        freq = by_rank.get(rank_reference)
    translation_ru = None
    ipa = None
    pos = None
    resolved_rank = rank_reference
    if freq:
        ipa = freq.get("ipa")
        pos = freq.get("pos")
        translation_ru = freq.get("translation_ru")
        if resolved_rank is None:
            resolved_rank = freq.get("rank")
        if not translation_en:
            translation_en = freq.get("translation_en")
    if not ipa:
        ipa = get_ipa(word)
    if not translation_ru and translation_en:
        try:
            translation_ru = translator.translate(translation_en)
        except Exception:
            translation_ru = None
    return {
        "word": word,
        "ipa": ipa,
        "translation_en": translation_en,
        "translation_ru": translation_ru,
        "pos": pos,
        "notes": None,
        "rank_reference": resolved_rank,
    }


def append_item(items, seen, item):
    word = item["word"]
    if word in seen:
        return
    seen.add(word)
    items.append(item)


def parse_standard(lines, by_word, by_rank, translator):
    items = []
    seen = set()
    started = False
    note_context = None
    for line in lines:
        if MAIN_ENTRY_RE.match(line) and started:
            break
        if line.startswith("Page "):
            continue
        if line in SECTION_NOTE_PREFIXES:
            note_context = SECTION_NOTE_PREFIXES[line]
            continue
        if line.startswith("-") and "(" in line:
            note_context = f"suffix={line.split()[0]}"
            continue
        match = STANDARD_LINE_RE.match(line)
        if not match:
            continue
        word = clean_line(match.group("word"))
        rank = int(match.group("rank"))
        meta = match.group("meta")
        gloss = clean_line(match.group("gloss"))
        if meta and meta not in META_TOKENS:
            gloss = f"{meta} {gloss}"
        item = enrich_item(word, gloss, rank, by_word, by_rank, translator)
        if note_context:
            item["notes"] = note_context
        append_item(items, seen, item)
        started = True
    return items


def parse_opposites(lines, by_word, by_rank, translator):
    items = []
    seen = set()
    tokens = []
    started = False
    for line in lines:
        if line.startswith("Page "):
            continue
        if MAIN_ENTRY_RE.match(line) and started:
            break
        if line in {"17 Opposites", "Opposites", "Comment: Note that in most cases the positive term ranks higher than the negative term.", "WORD 1", "WORD 2", "#", "DEF 1", "DEF 2"}:
            continue
        tokens.append(line)
        started = True
    for i in range(0, len(tokens) - 5, 6):
        word1, rank1, rank2, word2, gloss1, gloss2 = tokens[i:i+6]
        if not rank1.isdigit() or not rank2.isdigit():
            continue
        item1 = enrich_item(word1, gloss1, int(rank1), by_word, by_rank, translator)
        item1["notes"] = f"opposite_of={word2}"
        append_item(items, seen, item1)
        item2 = enrich_item(word2, gloss2, int(rank2), by_word, by_rank, translator)
        item2["notes"] = f"opposite_of={word1}"
        append_item(items, seen, item2)
    return items


def parse_se_pronoun(lines, by_word, by_rank, translator):
    items = []
    seen = set()
    started = False
    for line in lines:
        if line.startswith("Page "):
            continue
        if MAIN_ENTRY_RE.match(line) and started:
            break
        match = SE_LINE_RE.match(line)
        if not match:
            continue
        ratio = match.group("ratio")
        word = clean_line(match.group("word"))
        rank = int(match.group("rank"))
        gloss = clean_line(match.group("gloss"))
        item = enrich_item(word, gloss, rank, by_word, by_rank, translator)
        item["notes"] = f"se_usage_ratio={ratio}"
        append_item(items, seen, item)
        started = True
    return items


def parse_word_length(lines, by_word, by_rank, translator):
    items = []
    seen = set()
    tokens = []
    started = False
    in_table = False
    for line in lines:
        if line.startswith("Page "):
            continue
        if MAIN_ENTRY_RE.match(line) and in_table:
            break
        if line in {
            "27 Word length",
            "Word length",
            "Number of letters",
            "Unique word forms (types)",
            "Total number of occurrences (tokens)",
            "Most common words",
        }:
            if line == "Most common words":
                in_table = True
            continue
        if not in_table:
            continue
        if line.startswith("A commonly observed property") or line.startswith("This table shows") or line.startswith("The table also lists") or line.startswith("Conversely") or line.startswith("Over 9 million") or line.startswith("There are about") or line.startswith("happen to be") or line.startswith("and only about"):
            continue
        tokens.append(line)
        started = True
    i = 0
    while i + 3 < len(tokens):
        length = tokens[i]
        unique_types = tokens[i + 1]
        total_occurrences = tokens[i + 2]
        words_line = tokens[i + 3]
        i += 4
        if not re.fullmatch(r"\d+\+?|\d+", length):
            continue
        if not unique_types.isdigit() or not total_occurrences.isdigit():
            continue
        words = [clean_line(part) for part in words_line.split(",") if clean_line(part)]
        for word in words:
            freq = by_word.get(word)
            rank = freq.get("rank") if freq else None
            item = enrich_item(word, None, rank, by_word, by_rank, translator)
            item["notes"] = f"word_length={length}; unique_types={unique_types}; total_occurrences={total_occurrences}"
            append_item(items, seen, item)
    return items


def parse_category(doc, category, next_page, by_word, by_rank, translator):
    lines = []
    normalized_title = normalize_title(category["title"])
    for page_no in range(category["page"], next_page):
        page_text = get_page_text(doc, page_no)
        lines.extend(extract_segment(page_text, normalized_title, page_no == category["page"]))
    parser = category["parser"]
    if parser == "standard":
        return parse_standard(lines, by_word, by_rank, translator)
    if parser == "opposites":
        return parse_opposites(lines, by_word, by_rank, translator)
    if parser == "se_pronoun":
        return parse_se_pronoun(lines, by_word, by_rank, translator)
    if parser == "word_length":
        return parse_word_length(lines, by_word, by_rank, translator)
    raise ValueError(parser)


def main():
    doc = fitz.open(PDF_PATH)
    by_word, by_rank = load_frequency_lookup()
    translator = GoogleTranslator(source="en", target="ru")

    result = {}
    for idx, category in enumerate(CATEGORIES):
        next_page = CATEGORIES[idx + 1]["page"] if idx + 1 < len(CATEGORIES) else len(doc) + 1
        words = parse_category(doc, category, next_page, by_word, by_rank, translator)
        result[category["key"]] = {
            "id": category["id"],
            "title": category["title"],
            "words": words,
        }
        print(f"{category['id']:02d} {category['title']}: {len(words)}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()