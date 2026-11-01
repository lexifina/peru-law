"""Every unit line the full-stop fix changed (before/after corpus.d) must end '<line>”.' in the act's Editora Perú base
file: the same paragraph read by nlaunits before unquote(), so the restored '.' is the one printed after the mark.

    python -X utf8 more7/fsverify.py BEFORE_DIR
Prints one row per changed line and a count per part; exits 1 if any line is not found.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'more2'))
import fitz  # noqa: E402
import nlaunits  # noqa: E402

before = Path(sys.argv[1])
specs = {}
for s in (ROOT / 'more2').glob('*.json'):
    d = json.loads(s.read_text(encoding='utf-8'))
    if 'slug' in d and 'nla_id' in d:
        specs[d['slug']] = d
raw = {}


def paras(spec):
    k = (spec['nla_id'], spec['base']['capture'])
    if k not in raw:
        doc = fitz.open(nlaunits.path(*k))
        raw[k] = nlaunits.paragraphs(nlaunits.rows(doc))
    return raw[k]


count, bad = Counter(), 0
for fb in sorted((ROOT / 'corpus.d').glob('*.json')):
    a = json.loads((before / fb.name).read_text(encoding='utf-8'))
    b = json.loads(fb.read_text(encoding='utf-8'))
    if a == b:
        continue
    for xa, xb in zip(a['acts'], b['acts']):
        seen = set()
        for va, vb in zip(xa['versions'], xb['versions']):
            for f in ('units', 'changes'):
                ua, ub = va.get(f) or {}, vb.get(f) or {}
                for u in sorted(set(ua) | set(ub)):
                    la = (ua.get(u) or {}).get('text', '').splitlines()
                    lb = (ub.get(u) or {}).get('text', '').splitlines()
                    if len(la) != len(lb):
                        print('LINE COUNT', fb.name, u)
                        bad += 1
                        continue
                    for x, y in zip(la, lb):
                        if x == y:
                            continue
                        if y != x + '.':
                            print('NOT A FULL STOP', fb.name, u, repr(x[-40:]), repr(y[-40:]))
                            bad += 1
                            continue
                        if (u, y) in seen:      # the same base line carried into a later version
                            continue
                        seen.add((u, y))
                        ps = paras(specs[xb['slug']])
                        tail = ' '.join(x.split()[-8:])
                        # the paragraph ends there, or the spec's split_at cuts it right after the mark
                        hit = [p for p in ps if any((' '.join(p.split()) + ' ').find(tail + q + '. ') >= 0
                                                    for q in '”"')]
                        print('OK ' if hit else 'MISS', fb.name, vb['from'], u, '...' + y[-60:])
                        if hit:
                            count[fb.name] += 1
                        else:
                            bad += 1
for k, v in sorted(count.items()):
    print('fixed', k, v)
print('total', sum(count.values()), 'bad', bad)
sys.exit(1 if bad else 0)
