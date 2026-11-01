"""Amending sentences naming given acts in every cached card PDF (cache only).
    python -X utf8 more10/amctx.py 'Ley N?[°º.]* ?31572' ...   (one regex per act)"""
import glob, hashlib, json, re, sys
from pathlib import Path
import fitz
fitz.TOOLS.mupdf_display_errors(False)
ROOT = Path(__file__).resolve().parent.parent
AM = (r'(?:Modif[íi]c|Incorp[óo]r|Sustit[úu]y|Der[óo]g|Agr[ée]g|Adici[óo]n|Restit|Suspend|Dej[ae]se sin efecto|Prorr[óo]g)\w*\s+(?:el|los|la|las|un|una|lo)?\s*'
      r'(?:[\wáéíóú]+\s+)?(?:art[íi]culos?|literal|numeral|inciso|p[áa]rrafo|disposici|cap[íi]tulo|t[íi]tulo|anexo|Ley|Decreto|denominaci).{0,300}?(?:%s)\b')
rxs = [re.compile(AM % a, re.I) for a in sys.argv[1:]]
seen = set()
for f in sorted(glob.glob(str(ROOT / '.tmp/cards_*.jsonl'))):
    for l in open(f, encoding='utf-8'):
        c = json.loads(l)
        if not c.get('pdf') or c['pdf'] in seen:
            continue
        seen.add(c['pdf'])
        p = ROOT / '.cache' / hashlib.sha256(c['pdf'].encode()).hexdigest()
        if not p.exists():
            continue
        try:
            t = ' '.join(' '.join(pg.get_text() for pg in fitz.open(str(p))).split()).replace('ı́', 'í')
        except Exception:
            continue
        for a, rx in zip(sys.argv[1:], rxs):
            for m in rx.finditer(t):
                print(a, '|', c['op'], c['numero'], '|', t[max(0, m.start() - 80):m.end() + 60], flush=True)
print('done', len(seen), 'pdfs')
