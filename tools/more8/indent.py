"""Hidden paragraph breaks: rows set with a first-line indent, after a row ending in . : ; or ", that start inside a unit
line instead of at its start.  python -X utf8 more8/indent.py SPEC.json"""
import collections, json, re, sys
sys.path.insert(0, 'more2')
import fitz, nlaunits
s = json.load(open(sys.argv[1], encoding='utf-8'))
a = s['nla_args']
rs = nlaunits.rows(fitz.open(str(nlaunits.path(s['nla_id'], s['base']['capture']))))
left = collections.Counter()
for col, text, x0, *_ in rs:
    left[(col, round(x0))] += 1
lefts = {}
for (col, x), n in left.items():
    if n > 50 and (col not in lefts or x < lefts[col]):
        lefts[col] = x
u = nlaunits.units(s['nla_id'], s['base']['capture'], **a)
lines = [l for v in u.values() for l in v['lines']]
blob = '\n'.join(lines)
prev = ''
for col, text, x0, x1, right, bold, y in rs:
    t = text.strip()
    if (col in lefts and 8 < x0 - lefts[col] < 25 and re.search(r'[.:;]$', prev.strip()) and t[:1].isupper()):
        key = ' '.join(t.split()[:6])
        hit = [l for l in lines if key in l]
        if hit and not any(l.startswith(key) or l.startswith('“' + key) for l in hit):
            print('BREAK?', repr(prev.strip()[-40:]), '|', key)
    prev = t
