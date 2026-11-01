"""Prints the Constitution of Peru as it stood on a given day, read from this repository's history.

    python tools/vigente_el.py 2021-11-26 constitucion 112      # art. 112 under Ley 31280, the day before the TC struck it
    python tools/vigente_el.py 2021-11-27 constitucion 112      # the same article, restored by STC 918/2021
    python tools/vigente_el.py 2000-01-01 constitucion           # the whole Constitution on 1 January 2000
    python tools/vigente_el.py --law 2026-05-01 constitucion 90   # also name the law behind that wording

A thin wrapper around tools/on.py: the version is chosen by each commit's `In-force:` trailer, never by its commit
date, and branches named wip* are ignored. A bare article number (`112`, `7-a` for Artículo 7-A) means the article
(`art-112`, `art-007-a`); transitional provisions are `dft-01` ... `dft-16` and `dte-01` ... `dte-04`. Standard
library only.
"""
import re
import runpy
import sys
from pathlib import Path


def article(unit: str) -> str:
    m = re.fullmatch(r"(\d+)(?:-?([a-zA-Z]))?", unit)
    if not m:
        return unit
    return f"art-{int(m.group(1)):03d}" + (f"-{m.group(2).lower()}" if m.group(2) else "")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    args = [a for a in sys.argv[1:] if a != "--law"]
    if len(args) == 3:
        i = len(sys.argv) - 1 - sys.argv[::-1].index(args[2])
        sys.argv[i] = article(args[2])
    sys.argv[0] = str(Path(__file__).with_name("on.py"))
    runpy.run_path(sys.argv[0], run_name="__main__")
