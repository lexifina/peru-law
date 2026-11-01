"""Every listed norm (scan set 5 cards, cache only): sentences that amend an article of one of the scan-set-5 acts.
    python -X utf8 more4/amctx.py > more4/amctx.log"""
import json, re, sys, hashlib, os
from pathlib import Path
os.environ['ACTSET'] = '5'
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'more2'))
import fitz  # noqa: E402
from scan import ACTS  # noqa: E402
fitz.TOOLS.mupdf_display_errors(False)
C = ROOT / '.cache'
AM = (r'(?:Modif[íi]c|Incorp[óo]r|Sustit[úu]y|Der[óo]g|Agr[ée]g|Adici[óo]n)\w*\s+(?:el|los|la|las|un|una)\s+'
      r'(?:[\wáéíóú]+\s+)?(?:art[íi]culos?|literal|numeral|inciso|p[áa]rrafo|disposici|cap[íi]tulo|t[íi]tulo)[^.]{0,250}?(?:%s)')
hit = {}
for l in (ROOT / '.tmp/scan_multi5.jsonl').read_text(encoding='utf-8').splitlines():
    r = json.loads(l)
    if r.get('hits'):
        hit[r['op']] = r
cards = {}
for f in ('cards_cpc.jsonl', 'cards_decret.jsonl', 'cards_ley_decret.jsonl', 'cards_ley_decret_decret.jsonl'):
    for l in (ROOT / '.tmp' / f).read_text(encoding='utf-8').splitlines():
        c = json.loads(l)
        cards[c['op']] = c
for op, r in sorted(hit.items()):
    c = cards[op]
    p = C / hashlib.sha256(c['pdf'].encode()).hexdigest()
    if not p.exists():
        print(op, 'NOT CACHED'); continue
    t = ' '.join('\n'.join(pg.get_text() for pg in fitz.open(str(p))).split()).replace('ı́', 'í')
    for k in r['hits']:
        for m in re.finditer(AM % ACTS[k], t, re.I):
            print(op, c['numero'], k, '|', m.group(0)[:230], flush=True)
