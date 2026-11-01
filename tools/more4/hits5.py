"""Scan set 5 hits per act: python -X utf8 more4/hits5.py KEY [all] [ctx]  (default: only 'mod' hits)"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
k = sys.argv[1]
errs = 0
for l in (ROOT / '.tmp/scan_multi5.jsonl').read_text(encoding='utf-8').splitlines():
    r = json.loads(l)
    if r.get('error'):
        errs += 1
        continue
    h = (r.get('hits') or {}).get(k)
    if h and (h['mod'] or 'all' in sys.argv):
        print(r['op'], r['pub'], r['tipo'][:6], r['numero'], h['n'], h['mod'], '|', r['sumilla'][:150])
        if 'ctx' in sys.argv:
            for c in h['ctx'][:4]:
                print('        ', c[-260:])
print('errors', errs)
