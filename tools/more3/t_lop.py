import sys, re, json; sys.path.insert(0,'more2')
import nlaunits, nladiff
kw = dict(sumillas=True, bold_breaks=True, ord_heads=True, disp_prefix='dt', disp_label='transitoria',
          drop=r'^[“"]?Art[íi]culos\s+\d+\s+al\s+\d+')
a = nlaunits.units(4, '20260412', **kw)
for k, x in a.items():
    if not k.startswith('art'): print(k, x['label'], '|', x['lines'][0][:80], '|', len(x['lines']), '|', x['lines'][-1][-60:])
print(a['art-038']['lines'][-1][-100:])
b = nlaunits.units(4, '20251113', **kw)
for x in nladiff.diff(b, a): print(x[0], x[1], x[2][:150])
