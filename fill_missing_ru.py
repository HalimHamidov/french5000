import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from deep_translator import GoogleTranslator

BASE_DIR = Path(r"F:\Personal\BOOKS\Fr\5000")
INTERMEDIATE_PATH = BASE_DIR / "french_frequency_dictionary.intermediate.json"
FINAL_PATH = BASE_DIR / "french_frequency_dictionary.json"

_thread_local = threading.local()


def get_translator(src, tgt):
    key = f"{src}_{tgt}"
    cache = getattr(_thread_local, "cache", None)
    if cache is None:
        cache = {}
        _thread_local.cache = cache
    if key not in cache:
        cache[key] = GoogleTranslator(source=src, target=tgt)
    return cache[key]


def translate_one(text, src, tgt):
    if not text:
        return None
    for attempt in range(4):
        try:
            tr = get_translator(src, tgt)
            return tr.translate(text)
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    return None


def save_rows(path, rows):
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def fill_field(rows, source_field, target_field, src_lang, tgt_lang, max_workers=12):
    missing = [
        i
        for i, row in enumerate(rows)
        if row.get(source_field) and not row.get(target_field)
    ]
    total = len(missing)
    if total == 0:
        print(f"{target_field}: nothing to fill")
        return

    print(f"{target_field}: filling {total} items with {max_workers} workers")

    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(translate_one, rows[i][source_field], src_lang, tgt_lang): i
            for i in missing
        }
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                rows[i][target_field] = fut.result()
            except Exception:
                rows[i][target_field] = None

            completed += 1
            if completed % 100 == 0 or completed == total:
                save_rows(INTERMEDIATE_PATH, rows)
                filled = sum(1 for r in rows if r.get(target_field))
                print(f"{target_field}: {completed}/{total} done | filled={filled}")


def main():
    if not INTERMEDIATE_PATH.exists():
        raise RuntimeError("Intermediate file not found")

    with INTERMEDIATE_PATH.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    fill_field(rows, "translation_en", "translation_ru", "en", "ru", max_workers=12)
    save_rows(INTERMEDIATE_PATH, rows)

    fill_field(rows, "example_fr", "example_ru", "fr", "ru", max_workers=12)
    save_rows(INTERMEDIATE_PATH, rows)
    save_rows(FINAL_PATH, rows)

    total = len(rows)
    ipa = sum(1 for r in rows if r.get("ipa"))
    tr = sum(1 for r in rows if r.get("translation_ru"))
    ex = sum(1 for r in rows if r.get("example_ru"))
    print(f"DONE ipa={ipa}/{total} ru_tr={tr}/{total} ru_ex={ex}/{total}")


if __name__ == "__main__":
    main()
