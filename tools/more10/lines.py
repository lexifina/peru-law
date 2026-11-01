"""Lines of a cached El Peruano PDF with page/x0/x1/y, around a text: python -X utf8 more10/lines.py OP TEXT [N]"""
import hashlib, json, glob, sys
from pathlib import Path
import fitz
ROOT = Path(__file__).resolve().parent.parent
op, txt = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 4
pdf = None
for f in glob.glob(str(ROOT / '.tmp/cards_*.jsonl')):
    for l in open(f, encoding='utf-8'):
        c = json.loads(l)
        if c['op'] == op: pdf = c['pdf']
d = fitz.open(str(ROOT / '.cache' / hashlib.sha256(pdf.encode()).hexdigest()))
L = []
for pi, pg in enumerate(d):
    for b in pg.get_text('dict')['blocks']:
        for ln in b.get('lines', []):
            s = ''.join(sp['text'] for sp in ln['spans'])
            f = ln['spans'][0]['font'] if ln['spans'] else ''
            L.append((pi, round(ln['bbox'][0], 1), round(ln['bbox'][2], 1), round(ln['bbox'][1], 1), f[:18], s))
for i, x in enumerate(L):
    if txt in x[5]:
        for y in L[max(0, i - n):i + n + 1]:
            print(*y)
        print('--')
