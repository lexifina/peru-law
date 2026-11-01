"""Contexts naming the resoluciones legislativas 004-006-2025-2026-CR in the cached fuzzy search pages (no fetch).
    python -X utf8 more9/rlctx.py"""
import hashlib
import re
from pathlib import Path

C = Path(__file__).resolve().parent.parent / '.cache'
seen = set()
for q in ['004-2025-2026-CR', '005-2025-2026-CR', '006-2025-2026-CR']:
    u = 'https://busquedas.elperuano.pe/?query=' + q
    t = (C / hashlib.sha256(u.encode()).hexdigest()).read_text(encoding='utf8', errors='replace')
    t = ' '.join(t.replace('\\\\n', ' ').replace('\\n', ' ').replace('\\', ' ').split())
    for m in re.finditer(r'N[º°]\s*00[456]-2025-2026-CR', t):
        ctx = t[max(0, m.start() - 170):m.end() + 130]
        k = re.sub(r'\W', '', ctx[60:200])
        if k in seen:
            continue
        seen.add(k)
        print('-', ctx)
