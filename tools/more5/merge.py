"""Join single-act build_nla outputs (.tmp/p7/<name>.json) into one corpus.d part.

    python -X utf8 more5/merge.py PART.json NAME [NAME ...]
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
part, names = sys.argv[1], sys.argv[2:]
out = {'laws': {}, 'acts': [], 'sources': [], 'decisions': [], 'ai_use': []}
for n in names:
    p = json.loads((ROOT / '.tmp' / 'p7' / (n + '.json')).read_text(encoding='utf-8'))
    for k, law in p['laws'].items():
        if k in out['laws'] and out['laws'][k] != law:
            raise SystemExit(f'{n}: law {k} differs between acts')
        out['laws'][k] = law
    for f in ('acts', 'sources', 'decisions', 'ai_use'):
        out[f] += p[f]
out['laws'] = {k: out['laws'][k] for k in sorted(out['laws'])}
dst = ROOT / 'corpus.d' / part
tmp = dst.with_suffix('.json.tmp')
tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
os.replace(tmp, dst)
print('wrote', dst, len(out['acts']), 'acts', sum(len(a['versions']) for a in out['acts']), 'versions', len(out['laws']), 'laws')
