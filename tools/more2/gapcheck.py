"""Discovery: the laws El Peruano's search site does not list (read earlier from ADLP, El Peruano PDFs and MEF separatas,
all in ../.cache) checked for mentions of the acts in more2/scan.py."""
import json, re, sys, hashlib
from pathlib import Path
import fitz
fitz.TOOLS.mupdf_display_errors(False)
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
sys.path.insert(0, str(HERE)); from scan import ACTS, MOD
C = ROOT / '.cache'
items = []
for l in (ROOT / 'penal/.tmp/adlp_scan.jsonl').read_text(encoding='utf-8').splitlines():
    r = json.loads(l)
    if r.get('url'): items.append(('Ley %s' % r['n'], r['url']))
for r in json.loads((ROOT / 'penal/.tmp/gap_pdfs.json').read_text(encoding='utf-8')):
    if r.get('pdf'): items.append(('Ley %s' % r['n'], r['pdf']))
items += [('Ley 32441', 'https://cdn.www.gob.pe/uploads/document/file/8895416/7332535-ley32441.pdf?v=1761599743'),
          ('Ley 32732', 'https://cdn.www.gob.pe/uploads/document/file/10340261/8403069-ley32732.pdf?v=1784489960')]
for name, u in items:
    p = C / hashlib.sha256(u.encode()).hexdigest()
    if not p.exists():
        print(name, 'NOT CACHED', u); continue
    t = ' '.join('\n'.join(pg.get_text() for pg in fitz.open(str(p))).split())
    hs = {k: (len(re.findall(pat, t, re.I)), bool(re.search(MOD + r'\w*[^.]{0,250}(?:' + pat + ')', t, re.I))) for k, pat in ACTS.items() if re.search(pat, t, re.I)}
    if hs: print(name, hs, u[-40:])
print('checked', len(items))
