"""Unit-by-unit check of a spec's base parse against its NLA file: every body paragraph of the file (between the start and
end markers) must be inside some unit, or be a structure heading / a note-only line; every unit line must be a body
paragraph (or a part of one). Prints the uncovered paragraphs.

    python -X utf8 more4/cover.py more2/<spec>.json [capture]
"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'more2'))
import fitz, nlaunits  # noqa: E402

spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
nid = spec['nla_id']
ts = sys.argv[2] if len(sys.argv) > 2 else spec['base']['capture']
a = spec.get('nla_args', {})
us = nlaunits.units(nid, ts, **a)
if len(sys.argv) <= 2:          # the base version as build_nla makes it (hand base_fix units included)
    for k, v in spec.get('base_fix', {}).items():
        us.setdefault(k, {'label': k, 'kind': 'provision', 'lines': v})['lines'] = v
SIGN = re.compile(r'^(?:(?:Primer|Primera|Segund[oa]|Tercer[oa]?)\s+)?Vicepresident[ae]\s+del\s+Congreso|^President[ae]\s+del\s+Congreso')
ps = nlaunits.paragraphs(nlaunits.rows(fitz.open(str(nlaunits.path(nid, ts)))), a.get('bold_breaks', False), a.get('ord_heads', False))
for x, y in a.get('subs', ()):
    ps = [re.sub(x, y, p) for p in ps]
for rx in a.get('split_at', ()):
    ps = [q for p in ps for q in re.split(rx, p)]
for rx in a.get('join_next', ()):
    ps2 = []
    for p in ps:
        if ps2 and re.search(rx, ps2[-1]):
            ps2[-1] = ps2[-1] + ' ' + p
            continue
        ps2.append(p)
    ps = ps2
if a.get('notes') or a.get('drop') or a.get('drop2'):     # as nlaunits.units does
    ps2, skip = [], False
    for p in ps:
        if skip:
            skip = False
            continue
        if a.get('drop2') and re.match(a['drop2'], p):
            skip = True
            continue
        if a.get('drop') and re.match(a['drop'], p):
            continue
        for q in (re.split(a['notes'], p) if a.get('notes') else [p]):
            if q and q.strip():
                ps2.append(q.strip())
    ps = ps2


def w(s):
    s = re.sub(r'\(\d{1,3}\)(?=[A-Za-zÁÉÍÓÚáéíóúÑñ“"])', '', s) if a.get('fn_markers') else s
    return ' '.join(re.sub(r'[“”"]', ' ', s).split())


allu = ' \n '.join(w(l) for u in us.values() for l in u['lines'])
start = a.get('start_marker', 'TÍTULO PRELIMINAR')
idx = [i for i, p in enumerate(ps) if p.strip('“"') == start]
i0 = (idx[1] if len(idx) > 1 else idx[0]) if idx else next(i for i, p in enumerate(ps) if nlaunits.HSTRICT.match(p)) - 1
miss = 0
for p in ps[i0 + 1:]:
    if re.match(a.get('end_marker', r'^Comuníquese'), p):
        break
    q = w(nlaunits.unquote(p))
    if not q or q in allu:
        continue
    if nlaunits.STRUCT.match(p) or (p.upper() == p) or SIGN.match(p):
        continue
    # a paragraph split in two units (heading run into its text) is covered piecewise
    if all(part.strip() and part.strip() in allu for part in re.split(r'(?<=\.-)\s', q)):
        continue
    miss += 1
    print('NOT IN UNITS:', p[:220])
body = ' \n '.join(w(nlaunits.unquote(p)) for p in ps)
bad = 0
for k, u in us.items():
    for l in u['lines']:
        if w(l) not in body:
            bad += 1
            print('NOT IN FILE:', k, l[:200])
print(f'{nid} {ts}: {len(us)} units, {miss} body paragraphs outside units, {bad} unit lines not in the file')
