import json
import re
import time
from pathlib import Path

import gruut
from deep_translator import GoogleTranslator

BASE_DIR = Path(r"F:\Personal\BOOKS\Fr\5000")
INPUT_PATH = BASE_DIR / "french_frequency.json"
INTERMEDIATE_PATH = BASE_DIR / "french_frequency_dictionary.intermediate.json"
OUTPUT_PATH = BASE_DIR / "french_frequency_dictionary.json"
CKPT_PATH = BASE_DIR / "enrich_progress.json"

POS_MAP = {
    "nm": "noun",
    "nf": "noun",
    "nmi": "noun",
    "nfm": "noun",
    "nmf": "noun",
    "nmp": "noun",
    "nfp": "noun",
    "nmpl": "noun",
    "nfpl": "noun",
    "nadj": "adjective",
    "v": "verb",
    "adj": "adjective",
    "adji": "adjective",
    "adv": "adverb",
    "prep": "preposition",
    "conj": "conjunction",
    "det": "determiner",
    "art": "determiner",
    "pro": "pronoun",
    "pron": "pronoun",
    "intj": "interjection",
    "interj": "interjection",
    "excl": "interjection",
    "num": "numeral",
    "pfx": "phrase",
    "sfx": "phrase",
}

POS_PRIORITY = [
    "v",
    "adj",
    "nm",
    "nf",
    "nmi",
    "nfm",
    "nmf",
    "nmp",
    "nfp",
    "nmpl",
    "nfpl",
    "nadj",
    "adv",
    "prep",
    "det",
    "art",
    "conj",
    "pro",
    "pron",
    "num",
    "intj",
    "interj",
    "excl",
    "pfx",
    "sfx",
]


def normalize_pos(pos_str):
    if not pos_str:
        return None
    parts = [re.split(r"[(]", p)[0].strip() for p in pos_str.split(",")]
    for pref in POS_PRIORITY:
        if pref in parts:
            return POS_MAP.get(pref)
    return POS_MAP.get(parts[0]) if parts else None


def get_ipa(word):
    try:
        sents = list(gruut.sentences(word, lang="fr"))
        phones = []
        for sent in sents:
            for tok in sent.words:
                if tok.is_spoken and tok.phonemes:
                    phones.extend(tok.phonemes)
        if phones:
            return "/" + "".join(phones) + "/"
    except Exception:
        return None
    return None


def load_json(path, default):
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_base(entries):
    output = []
    for e in entries:
        output.append(
            {
                "id": e["rank"],
                "rank": e["rank"],
                "word": e["word"],
                "lemma": e["word"],
                "ipa": None,
                "pos": normalize_pos(e.get("pos")),
                "translation_en": e.get("translation_en"),
                "translation_ru": None,
                "example_fr": e.get("example_fr"),
                "example_en": e.get("example_en"),
                "example_ru": None,
                "collocations": [],
                "semantic_cluster": None,
                "audio": None,
                "notes": None,
            }
        )
    return output


def count_filled(rows, key):
    return sum(1 for r in rows if r.get(key) not in (None, ""))


def progress_log(rows):
    return {
        "total": len(rows),
        "ipa_filled": count_filled(rows, "ipa"),
        "translation_ru_filled": count_filled(rows, "translation_ru"),
        "example_ru_filled": count_filled(rows, "example_ru"),
    }


def main():
    entries = load_json(INPUT_PATH, [])
    if not entries:
        raise RuntimeError("Input file is empty or missing")

    state = load_json(
        CKPT_PATH,
        {
            "stage": "ipa",
            "index": 0,
            "rows": build_base(entries),
        },
    )

    rows = state["rows"]
    if len(rows) != len(entries):
        state = {"stage": "ipa", "index": 0, "rows": build_base(entries)}
        rows = state["rows"]

    save_json(INTERMEDIATE_PATH, rows)

    # Stage 1: IPA
    if state["stage"] == "ipa":
        i = int(state["index"])
        for idx in range(i, len(rows)):
            if rows[idx]["ipa"] is None:
                rows[idx]["ipa"] = get_ipa(rows[idx]["word"])
            if (idx + 1) % 100 == 0 or idx + 1 == len(rows):
                state["index"] = idx + 1
                state["rows"] = rows
                save_json(CKPT_PATH, state)
                save_json(INTERMEDIATE_PATH, rows)
                p = progress_log(rows)
                print(f"IPA {idx + 1}/{len(rows)} | ipa={p['ipa_filled']}")
        state["stage"] = "translation_ru"
        state["index"] = 0
        state["rows"] = rows
        save_json(CKPT_PATH, state)

    # Stage 2: EN -> RU (translation field)
    if state["stage"] == "translation_ru":
        translator = GoogleTranslator(source="en", target="ru")
        i = int(state["index"])
        chunk_size = 120
        for start in range(i, len(rows), chunk_size):
            end = min(start + chunk_size, len(rows))
            payload_idx = []
            payload_text = []
            for idx in range(start, end):
                text = rows[idx]["translation_en"]
                if text and not rows[idx]["translation_ru"]:
                    payload_idx.append(idx)
                    payload_text.append(text)

            if payload_text:
                try:
                    translated = translator.translate_batch(payload_text)
                except Exception:
                    translated = []
                    for text in payload_text:
                        try:
                            translated.append(translator.translate(text))
                        except Exception:
                            translated.append(None)

                for pos, idx in enumerate(payload_idx):
                    if pos < len(translated):
                        rows[idx]["translation_ru"] = translated[pos]

            state["index"] = end
            state["rows"] = rows
            save_json(CKPT_PATH, state)
            save_json(INTERMEDIATE_PATH, rows)
            p = progress_log(rows)
            print(
                f"TR {end}/{len(rows)} | ru_tr={p['translation_ru_filled']} "
                f"ru_ex={p['example_ru_filled']}"
            )
        state["stage"] = "example_ru"
        state["index"] = 0
        state["rows"] = rows
        save_json(CKPT_PATH, state)

    # Stage 3: FR -> RU (example field)
    if state["stage"] == "example_ru":
        translator = GoogleTranslator(source="fr", target="ru")
        i = int(state["index"])
        chunk_size = 120
        for start in range(i, len(rows), chunk_size):
            end = min(start + chunk_size, len(rows))
            payload_idx = []
            payload_text = []
            for idx in range(start, end):
                text = rows[idx]["example_fr"]
                if text and not rows[idx]["example_ru"]:
                    payload_idx.append(idx)
                    payload_text.append(text)

            if payload_text:
                try:
                    translated = translator.translate_batch(payload_text)
                except Exception:
                    translated = []
                    for text in payload_text:
                        try:
                            translated.append(translator.translate(text))
                        except Exception:
                            translated.append(None)

                for pos, idx in enumerate(payload_idx):
                    if pos < len(translated):
                        rows[idx]["example_ru"] = translated[pos]

            state["index"] = end
            state["rows"] = rows
            save_json(CKPT_PATH, state)
            save_json(INTERMEDIATE_PATH, rows)
            p = progress_log(rows)
            print(
                f"EX {end}/{len(rows)} | ru_tr={p['translation_ru_filled']} "
                f"ru_ex={p['example_ru_filled']}"
            )
        state["stage"] = "done"
        state["index"] = len(rows)
        state["rows"] = rows
        save_json(CKPT_PATH, state)

    save_json(OUTPUT_PATH, rows)
    save_json(INTERMEDIATE_PATH, rows)
    p = progress_log(rows)
    print(
        "DONE "
        f"ipa={p['ipa_filled']}/{p['total']} "
        f"ru_tr={p['translation_ru_filled']}/{p['total']} "
        f"ru_ex={p['example_ru_filled']}/{p['total']}"
    )


if __name__ == "__main__":
    main()
