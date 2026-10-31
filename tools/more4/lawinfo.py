"""For scan-set-5 ops: the card, the PDF's page date line, and the norm's paragraphs (optionally grepped).
    python -X utf8 more4/lawinfo.py OP [grep=RE] [width=N] [all]"""
import json, re, sys, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'more2')); sys.path.insert(0, str(ROOT / 'penal'))
import fitz, build_nla  # noqa: E402
op = sys.argv[1]
g = [x[5:] for x in sys.argv[2:] if x.startswith('grep=')]
w = int(([x[6:] for x in sys.argv[2:] if x.startswith('width=')] or ['260'])[0])
card = None
for f in ('cards_cpc.jsonl', 'cards_decret.jsonl', 'cards_ley_decret.jsonl', 'cards_ley_decret_decret.jsonl'):
    for l in (ROOT / '.tmp' / f).read_text(encoding='utf-8').splitlines():
        c = json.loads(l)
        if c['op'] == op:
            card = c
print(json.dumps(card, ensure_ascii=False))
p = ROOT / '.cache' / hashlib.sha256(card['pdf'].encode()).hexdigest()
doc = fitz.open(str(p))
t = doc[0].get_text()
m = re.search(r'(lunes|martes|mi[ée]rcoles|jueves|viernes|s[áa]bado|domingo)\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}', t, re.I)
print('PAGE DATE:', m.group(0) if m else '?')
num = re.sub(r'\D', '', card['numero'].split('-')[0]) if 'URGENCIA' not in card['tipo'] else card['numero'].split()[-1]
kind = {'LEY': r'ley', 'DECRETO LEGISLATIVO': r'decreto\s+legislativo', 'DECRETO DE URGENCIA': r'decreto\s+de\s+urgencia'}.get(card['tipo'], r'ley')
head = kind + r'\s*n?\s*[°º.]?\s*' + re.escape(num)
print('HEADING:', head)
ps, sha = build_nla.law_paras({'pdf': card['pdf'], 'op': op, 'heading': head})
for i, q in enumerate(ps):
    if 'all' in sys.argv or not g or re.search(g[0], q, re.I):
        print(i, q[:w])
