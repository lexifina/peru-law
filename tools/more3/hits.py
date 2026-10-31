"""Scan hits for one act key since an op number: python -X utf8 more3/hits.py FILE KEY [MIN_OP] [ctx]"""
import json, sys
from pathlib import Path
cards = {}
for f in ('cards_cpc.jsonl', 'cards_decret.jsonl'):
    for l in open('.tmp/' + f, encoding='utf8'):
        c = json.loads(l); cards[c['op']] = c
for l in Path('.tmp/' + sys.argv[1]).read_text(encoding='utf-8').splitlines():
    r = json.loads(l)
    h = (r.get('hits') or {}).get(sys.argv[2]) if isinstance(r.get('hits'), dict) else None
    if h and r['op'] >= (sys.argv[3] if len(sys.argv) > 3 else ''):
        print(r['tipo'][:6], r['numero'], r['op'], (cards.get(r['op'], {}).get('range') or [''])[0], h['n'], h['mod'], r['sumilla'][:110])
        if 'ctx' in sys.argv:
            for c in h['ctx'][:3]: print('        ', c[-260:])
