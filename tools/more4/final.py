"""Units of a part as of a date (default: last version): python -X utf8 more4/final.py corpus.d/<part>.json [KEY ...] [@YYYY-MM-DD]"""
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
keys = [a for a in sys.argv[2:] if not a.startswith('@')]
at = ([a[1:] for a in sys.argv[2:] if a.startswith('@')] or ['9999'])[0]
for act in p['acts']:
    units = {}
    for v in act['versions']:
        if v['from'] > at:
            break
        if 'units' in v:
            units = dict(v['units'])
        for k, u in (v.get('changes') or {}).items():
            if u is None:
                units.pop(k, None)
            else:
                units[k] = u
    print(act['slug'], len(units), 'units')
    for k in keys or sorted(units):
        print('--', k, units.get(k, {}).get('label'))
        print(units.get(k, {}).get('text', 'MISSING\n'), end='')
