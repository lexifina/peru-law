"""Gap laws (gapcheck items): sentences that amend an article of one of the scan-set-5 acts.
    python -X utf8 more4/gapctx.py"""
import json, re, sys, hashlib, os
from pathlib import Path
os.environ['ACTSET'] = '5'
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'more2'))
import fitz  # noqa: E402
from scan import ACTS  # noqa: E402
C = ROOT / '.cache'
items = []
for l in (ROOT / 'penal/.tmp/adlp_scan.jsonl').read_text(encoding='utf-8').splitlines():
    r = json.loads(l)
    if r.get('url'): items.append(('Ley %s' % r['n'], r['url']))
for r in json.loads((ROOT / 'penal/.tmp/gap_pdfs.json').read_text(encoding='utf-8')):
    if r.get('pdf'): items.append(('Ley %s' % r['n'], r['pdf']))
items += [('Ley 32441', 'https://cdn.www.gob.pe/uploads/document/file/8895416/7332535-ley32441.pdf?v=1761599743'),
          ('Ley 32732', 'https://cdn.www.gob.pe/uploads/document/file/10340261/8403069-ley32732.pdf?v=1784489960')]
AM = r'(?:Modif[íi]ca|Incorp[óo]ra|Sustit[úu]ye|Der[óo]ga)\w*\s+(?:el|los|la|las)\s+(?:art[íi]culos?|literal|numeral|inciso|p[áa]rrafo|disposici)[^.]{0,200}?(?:%s)'
for name, u in items:
    p = C / hashlib.sha256(u.encode()).hexdigest()
    if not p.exists():
        continue
    t = ' '.join('\n'.join(pg.get_text() for pg in fitz.open(str(p))).split())
    for k, pat in ACTS.items():
        for m in re.finditer(AM % pat, t, re.I):
            print(name, k, '|', m.group(0)[:260])
