"""Metadata + page-1 image size of no-text NLA captures (cache only)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'more2'))
import nlaunits, fitz
fitz.TOOLS.mupdf_display_errors(False)
for a in sys.argv[1:]:
    nid, ts = a.split(':')
    p = nlaunits.path(nid, ts)
    if not p.exists():
        print(a, 'not cached'); continue
    try:
        d = fitz.open(str(p))
        print(a, d.page_count, d.metadata, flush=True)
    except Exception as e:
        print(a, 'ERR', e)
