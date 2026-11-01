"""The issue texts of 6 Dec 2025 - 17 Jan 2026 (El Peruano's date index lists no norm then), cached by penal/issues.py:
grep them.   python -X utf8 more4/gapissues.py REGEX [width]"""
import datetime as dt, hashlib, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
C = ROOT / '.cache'
rx = re.compile(sys.argv[1], re.I)
w = int(sys.argv[2]) if len(sys.argv) > 2 else 200
d, e = dt.date(2025, 12, 6), dt.date(2026, 1, 17)
n = miss = 0
while d <= e:
    for p in ('NL', 'EX'):
        u = 'https://busquedas.elperuano.pe/?query=' + p + d.strftime('%Y%m%d')
        f = C / hashlib.sha256(u.encode()).hexdigest()
        if not f.exists():
            miss += 1
            continue
        n += 1
        t = f.read_bytes().decode('utf8', 'replace').replace('\\\\n', '\n').replace('\\n', '\n').replace('\\"', '"')
        t = ' '.join(t.split())
        for m in rx.finditer(t):
            print(p + d.strftime('%Y%m%d'), '|', t[max(0, m.start() - w):m.end() + w])
    d += dt.timedelta(1)
print('issues read', n, 'not cached', miss)
