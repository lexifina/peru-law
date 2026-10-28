"""Check corpus.json against the reform laws themselves (ADLP texts, where the cache holds a text PDF).

For every version credited to such a law, each paragraph the law added or changed must occur, word for
word (typography-insensitive), in the law's own text. Reads the cache only; writes nothing.

    python -X utf8 verify_laws.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import editions as E  # noqa: E402
import fetch  # noqa: E402


def main() -> int:
    corpus = json.loads((HERE / "corpus.json").read_text(encoding="utf-8"))
    vs = corpus["acts"][0]["versions"]
    bad = checked = 0
    for key, law in sorted(corpus["laws"].items()):
        url = law["url"]
        if not url.endswith(".pdf") or not fetch.cached(url) or key == "constitucion-1993":
            print(f"{key}: no text in the cache")
            continue
        text = E.words(" ".join(r.text for r in E.rows_of(url)))
        if len(text) < 200:
            print(f"{key}: the cached PDF is a scan (no text layer)")
            continue
        n = 0
        for i, v in enumerate(vs):
            for unit, laws in v["credits"].items():
                if key not in laws or unit not in v["units"]:
                    continue
                old = set(vs[i - 1]["units"].get(unit, {}).get("text", "").splitlines()) if i else set()
                for line in v["units"][unit]["text"].splitlines()[1:]:
                    if line in old:
                        continue
                    n += 1
                    if E.words(line) not in text:
                        bad += 1
                        print(f"{key} {v['from']} {unit}: NOT in the law: {line[:110]}")
        checked += n
        print(f"{key}: {n} changed paragraphs checked")
    print(f"total {checked} paragraphs checked, {bad} not found")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
