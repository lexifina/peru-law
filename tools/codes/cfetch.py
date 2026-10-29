"""Fetch helper for the codes part (Código Civil, Ley 29733).

Thin wrapper around ../fetch.py: same cache (../.cache, sha256 of the URL), same
request log, same User-Agent, curl with --compressed. Requests are spaced
1.5 s per host because another agent may be using the same hosts.

    python -X utf8 codes/cfetch.py URL [URL ...]
    python -X utf8 codes/cfetch.py --plan        fetch everything in codes/sources.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import fetch  # noqa: E402

_orig_get = fetch.get
_last: dict[str, float] = {}


def get(url: str, **kw):
    if not kw.get("force") and fetch.cached(kw.get("cache_as") or url):
        return fetch.cached(kw.get("cache_as") or url)
    host = urlparse(url).netloc
    wait = 1.5 - (time.time() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.time()
    return _orig_get(url, **kw)


def plan_urls() -> list[str]:
    src = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    out: list[str] = []
    for item in src.values():
        out.extend(item.get("urls", []))
    return out


def main(argv: list[str]) -> int:
    force = "--force" in argv
    argv = [a for a in argv if a != "--force"]
    urls = plan_urls() if argv[:1] == ["--plan"] else argv
    bad = 0
    for u in urls:
        p = get(u, force=force)
        info = json.loads(fetch.meta_for(u).read_text(encoding="utf-8"))
        print(info["status"], info["bytes"], info["type"], u, "->", p.name if p else "FAILED")
        bad += p is None
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
