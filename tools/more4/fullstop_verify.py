"""Each unit changed by the full-stop fix: its rebuilt line vs the same line in every later Editora Perú checkpoint of
the part's spec (exact text), and vs the amending law's own paragraph (must end '<line>”.').
    python -X utf8 more4/fullstop_verify.py more4/fullstop_diff.txt"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'more2')); sys.path.insert(0, str(ROOT / 'penal'))
import nlaunits, build_nla  # noqa: E402
specs = {}
for sp in (ROOT / 'more2').glob('*.json'):
    s = json.loads(sp.read_text(encoding='utf-8')); specs[s['part']] = s
cache = {}
for row in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
    part, vfrom, key = row.split()[:3]
    p = json.loads((ROOT / 'corpus.d' / part).read_text(encoding='utf-8'))
    units = {}
    for v in p['acts'][0]['versions']:
        if v['from'] > vfrom: break
        units.update(v.get('units') or {})
        for k, u in (v.get('changes') or {}).items():
            if u: units[k] = u
    tail = eval(row.rsplit('-> ...', 1)[1])
    line = [l for l in units[key]['text'].splitlines() if l.endswith(tail)][-1]
    lawok = None
    s = specs.get(part)
    res = []
    if s:
        law = next(l for l in s['laws'] if l['in_force'] == vfrom and key in l['compose'])
        ps, _ = build_nla.law_paras(law)
        lawok = any(q.rstrip().endswith(line[-60:-1] + '”.') or q.rstrip().endswith(line[-60:-1] + '".') for q in ps)
        for c in s['checkpoints']:
            if c['date'] >= vfrom:
                ck = (s['nla_id'], c['capture'])
                if ck not in cache: cache[ck] = nlaunits.units(s['nla_id'], c['capture'], **s.get('nla_args', {}))
                cu = cache[ck].get(key)
                cl = [l for l in (cu or {}).get('lines', []) if line[-60:-1] in l]
                res.append(f"{c['id']}: " + ('exact' if any(l == line for l in cl) else
                                             ('ends ' + repr(cl[0][-12:]) if cl else 'line not found')))
    print(part, vfrom, key, '| law paragraph ends "' + line[-25:-1] + '”.":', lawok, '|', '; '.join(res) or 'no later checkpoint')
