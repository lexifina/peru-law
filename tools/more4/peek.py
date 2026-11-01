"""Units of an NLA capture with build_nla args (debugging).
    python -X utf8 more4/peek.py ID TS 'JSON-ARGS' [KEY ...|keys|paras A B]"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'more2'))
import nlaunits, fitz  # noqa: E402

if sys.argv[1].endswith('.json'):      # a spec: its NLA id, base capture and args
    _s = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    nid, ts, args, rest = _s['nla_id'], _s['base']['capture'], _s.get('nla_args', {}), sys.argv[2:]
else:
    nid, ts, args = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    rest = sys.argv[4:]
if rest[:1] == ['paras']:
    ps = nlaunits.paragraphs(nlaunits.rows(fitz.open(str(nlaunits.path(nid, ts)))), args.get('bold_breaks', False),
                             args.get('ord_heads', False))
    a, b = int(rest[1]), int(rest[2])
    for i, p in enumerate(ps[a:b], a):
        print(i, p[:200])
    sys.exit()
us = nlaunits.units(nid, ts, **args)
print(len(us), 'units')
if rest == ['keys']:
    print(' '.join(us))
    sys.exit()
for k in rest or list(us):
    u = us.get(k)
    if not u:
        print(k, 'MISSING'); continue
    print(k, '|', u['label'])
    for l in u['lines']:
        print('   |', l[:240])
