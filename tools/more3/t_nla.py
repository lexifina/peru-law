"""Parse several captures of one NLA idNorma and diff consecutive ones:
   python -X utf8 more3/t_nla.py SPEC_OR_ID TS1 TS2 [TS3 ...]   (SPEC: a more2/*.json whose nla_args are used)"""
import sys, json; sys.path.insert(0, 'more2')
import nlaunits, nladiff
a0 = sys.argv[1]
if a0.endswith('.json'):
    s = json.load(open(a0, encoding='utf8')); nid, kw = s['nla_id'], s.get('nla_args', {})
else:
    nid, kw = int(a0), {'sumillas': True, 'bold_breaks': True}
prev = None
for ts in sys.argv[2:]:
    u = nlaunits.units(nid, ts, **kw)
    print('==', ts, len(u), 'units', list(u)[:2], list(u)[-3:])
    if prev:
        for x in nladiff.diff(prev, u): print('  ', x[0], x[1], x[2][:300])
    prev = u
