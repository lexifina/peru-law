"""Words a text layer runs together ("legalmenteestablecida"): tokens of a part's units that are not known words but split
into two known ones; vocabulary from other Editora Perú files in the cache.
    python -X utf8 more4/glued.py more2/<spec>.json [...]"""
import collections, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'more2'))
import fitz, nlaunits  # noqa: E402
VOC = collections.Counter()
for nid, ts in [(60, '20250708'), (2, '20260816'), (70003, '20260224'), (90009, '20260714'), (12, '20250411'), (15, '20230609')]:
    t = ''.join(p.get_text() for p in fitz.open(str(nlaunits.path(nid, ts))))
    VOC.update(w.lower() for w in re.findall(r'[^\W\d_]+', t))
for sp in sys.argv[1:]:
    s = json.loads(Path(sp).read_text(encoding='utf-8'))
    us = nlaunits.units(s['nla_id'], s['base']['capture'], **s.get('nla_args', {}))
    for k, u in us.items():
        for l in u['lines']:
            for m in re.finditer(r'[^\W\d_]+(?:,[^\W\d_]+)?', l):
                w = m.group(0)
                if ',' in w:
                    print(sp, k, 'COMMA', w)
                    continue
                if VOC[w.lower()] >= 2 or len(w) < 6:
                    continue
                for i in range(2, len(w) - 1):
                    a, b = w[:i].lower(), w[i:].lower()
                    SUF = {'mente', 'miento', 'dos', 'das', 'ción', 'ciones', 'rán', 'dad', 'tes', 'les', 'es', 'se', 'do',
                           'da', 'ria', 'rios', 'tivo', 'tivos', 'tales', 'ya', 'rados', 'grados', 'ponen', 'cargo'}
                    stop = {'de', 'la', 'el', 'en', 'al', 'por', 'como', 'del', 'que', 'los', 'las', 'con', 'a', 'y'}
                    ok = (a in stop or b in stop or (VOC[a] >= 30 and VOC[b] >= 30 and len(a) > 3 and len(b) > 3))                         and b not in SUF and a not in ('re', 'in', 'ex', 'pre', 'con', 'inter', 'tra')
                    if ok and VOC[a] >= 3 and VOC[b] >= 3:
                        print(sp, k, w, '->', w[:i], w[i:])
                        break
