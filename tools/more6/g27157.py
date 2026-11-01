"""Grep the cached El Peruano search pages (more6/q27157.py queries) for reglamentos of D.Leg 1568 / 1595, plain find."""
import hashlib, re, sys, urllib.parse
from pathlib import Path
C = Path(__file__).resolve().parent.parent / '.cache'
qs = ["Reglamento del Decreto Legislativo 1568", "Reglamento del Decreto Legislativo 1595",
      "régimen jurídico de la propiedad horizontal reglamento"]
seen = set()
for q in qs:
    p = C / hashlib.sha256(('https://busquedas.elperuano.pe/?query=' + urllib.parse.quote(q)).encode()).hexdigest()
    if not p.exists():
        print('not cached', q); continue
    t = p.read_bytes().decode('utf-8', 'replace')
    for key in ('Legislativo N° 1568', 'Legislativo Nº 1568', 'Legislativo 1568', 'Legislativo N° 1595', 'Legislativo Nº 1595', 'Legislativo 1595'):
        i = 0
        while True:
            i = t.find(key, i)
            if i < 0: break
            s = ' '.join(re.sub(r'<[^>]*>', ' ', t[max(0, i - 220):i + 120]).split())
            i += len(key)
            if 'eglamento' in s and s[:80] not in seen:
                seen.add(s[:80]); print(q[:30], '|', s)
