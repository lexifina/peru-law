"""Before/after diff of corpus.d parts: every changed unit per version, and any other field that differs.
    python -X utf8 more4/partdiff.py BEFORE_DIR [AFTER_DIR=corpus.d]"""
import json, sys
from pathlib import Path
A = Path(sys.argv[1]); B = Path(sys.argv[2] if len(sys.argv) > 2 else 'corpus.d')
for fb in sorted(B.glob('*.json')):
    fa = A / fb.name
    a, b = json.loads(fa.read_text(encoding='utf-8')), json.loads(fb.read_text(encoding='utf-8'))
    if a == b:
        continue
    for k in set(a) | set(b):
        if k != 'acts' and a.get(k) != b.get(k):
            if isinstance(a.get(k), list):
                for x in a[k]:
                    if x not in b[k]: print(fb.name, k, '- ', str(x)[:300])
                for x in b[k]:
                    if x not in a[k]: print(fb.name, k, '+ ', str(x)[:300])
            else:
                print(fb.name, 'FIELD', k, 'differs')
    for xa, xb in zip(a['acts'], b['acts']):
        ka = {k: v for k, v in xa.items() if k != 'versions'}; kb = {k: v for k, v in xb.items() if k != 'versions'}
        if ka != kb: print(fb.name, 'ACT FIELDS differ')
        if len(xa['versions']) != len(xb['versions']): print(fb.name, 'VERSION COUNT differs')
        for va, vb in zip(xa['versions'], xb['versions']):
            for f in set(va) | set(vb):
                if f in ('units', 'changes'):
                    ua, ub = va.get(f) or {}, vb.get(f) or {}
                    for u in sorted(set(ua) | set(ub)):
                        if ua.get(u) != ub.get(u):
                            ta = (ua.get(u) or {}).get('text', ''); tb = (ub.get(u) or {}).get('text', '')
                            la, lb = ta.splitlines(), tb.splitlines()
                            d = [(x, y) for x, y in zip(la, lb) if x != y]
                            print(fb.name, vb['from'], u, 'lines', len(la), '->', len(lb), '|', ' || '.join(f'...{x[-45:]!r} -> ...{y[-45:]!r}' for x, y in d))
                elif va.get(f) != vb.get(f):
                    print(fb.name, vb['from'], 'VERSION FIELD', f, 'differs')
