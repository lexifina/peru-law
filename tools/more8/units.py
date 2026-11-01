"""Base units of an NLA capture with a spec's args (or the defaults A + extra json):
    python -X utf8 more8/units.py SPEC.json|ID:TS [KEY..]      (KEY 'all' prints every unit in full)"""
import json, sys
from pathlib import Path
sys.path.insert(0, 'more2'); sys.path.insert(0, 'more5'); sys.path.insert(0, 'more8')
import nlaunits
from specs import A
a = sys.argv[1]
if a.endswith('.json'):
    s = json.loads(Path(a).read_text(encoding='utf-8'))
    nid, ts, args = s['nla_id'], s['base']['capture'], s.get('nla_args', {})
else:
    nid, ts = a.split(':')
    nid = int(nid)
    import pens
    args = pens.ARGS.get(nid, A)
u = nlaunits.units(nid, ts, **args)
keys = sys.argv[2:]
for k, v in u.items():
    if keys and k not in keys and keys != ['all']:
        continue
    if keys:
        print('==', k, v['label']); print('\n'.join(v['lines']))
    else:
        print(k, '|', v['lines'][0][:100], '| n', len(v['lines']))
print('units', len(u))
