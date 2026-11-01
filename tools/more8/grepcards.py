"""Grep the cached PDFs of every listed card (cache only): python -X utf8 more8/grepcards.py REGEX [FROM_OP_PREFIX]
Prints op, numero and up to 3 contexts per hit. Optional second arg: only cards whose op >= this number."""
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
fitz.TOOLS.mupdf_display_errors(False)
rx = re.compile(sys.argv[1], re.I)
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
seen = set()
for f in sorted((ROOT / '.tmp').glob('cards_*.jsonl')):
    for l in f.read_text(encoding='utf-8').splitlines():
        c = json.loads(l)
        if c['op'] in seen or not c.get('pdf') or int(c['op'].split('-')[0]) < lo:
            continue
        seen.add(c['op'])
        p = ROOT / '.cache' / hashlib.sha256(c['pdf'].encode()).hexdigest()
        if not p.exists():
            continue
        try:
            t = ' '.join(pg.get_text() for pg in fitz.open(str(p)))
        except Exception:
            continue
        t = ' '.join(t.split())
        ms = list(rx.finditer(t))
        if ms:
            print(c['op'], c['tipo'], c['numero'], '|', c['sumilla'][:90])
            for m in ms[:3]:
                print('   ', t[max(0, m.start() - 200):m.end() + 200])
