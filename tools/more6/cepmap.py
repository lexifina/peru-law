"""Numbering map Decreto Legislativo 654 -> TUO del Código de Ejecución Penal (DS 003-2021-JUS), from the TUO's own
concordance notes ("(Texto según el artículo N del Decreto Legislativo N° 654 ...)") in Editora Perú's file (NLA 70006,
capture 20250523). A note follows the text of the TUO article it belongs to.

    python -X utf8 more6/cepmap.py [ART ...]     (no ART: write more6/cepmap.json and print a summary)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import fitz

fitz.TOOLS.mupdf_display_errors(False)
ROOT = Path(__file__).resolve().parent.parent
U = 'https://web.archive.org/web/20250523id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=70006'
doc = fitz.open(str(ROOT / '.cache' / hashlib.sha256(U.encode()).hexdigest()))
t = ' '.join(''.join(p.get_text() for p in doc).split())
# the TUO body: from its own "TÍTULO PRELIMINAR" (after the approving decree) to the reglamento
a = t.index('TEXTO ÚNICO ORDENADO DEL CÓDIGO DE EJECUCIÓN PENAL', 2000)
b = t.find('REGLAMENTO DEL CÓDIGO DE EJECUCIÓN PENAL', a)
body = t[a:b if b > 0 else None]
HEAD = re.compile(r'(?:^|(?<=[\s.”"]))[“"]?Art[íi]culo\s+([IVX]+|\d+(?:-[A-Z])?)\s*[°º]?\s*(?:\.?-|\.\s+(?=[A-ZÁÉÍÓÚ]))')
DISP = re.compile(r'(?:^|(?<=[\s.”"]))[“"]?((?:Primera|Segunda|Tercera|Cuarta|Quinta|Sexta|S[ée]ptima|Octava|Novena|'
                  r'D[ée]cima|Und[ée]cima)[\w ]{0,12})\s*\.?-')
NOTE = re.compile(r'\((?:Texto|P[áa]rrafo|Numeral|Art[íi]culo|Literal)[^()]{0,60}?según\s+(?:el|la|los|las)\s+'
                  r'([^()]{0,200}?)Decreto\s+Legislativo\s+N?[°º]?\s*654([^()]*)\)')
events = sorted([(m.start(), 'h', m.group(1)) for m in HEAD.finditer(body)]
                + [(m.start(), 'n', m.group(1).strip(), m.group(2).strip()) for m in NOTE.finditer(body)])
cur, m, notes = None, {}, 0
for e in events:
    if e[1] == 'h':
        # a heading inside a quoted note text is not a new article; real headings come in TUO order
        cur = e[2]
        continue
    notes += 1
    if cur:
        m.setdefault(cur, []).append(' '.join(e[2].split()))
rev = {}
for k, vs in m.items():
    for v in vs:
        for n in re.findall(r'art[íi]culos?\s+((?:[IVX]+|\d+(?:-[A-Z])?)(?:\s*(?:,|y)\s*(?:[IVX]+|\d+(?:-[A-Z])?))*)', v):
            for x in re.split(r'\s*(?:,|y)\s*', n):
                rev.setdefault(x, []).append(k)
if len(sys.argv) > 1:
    for x in sys.argv[1:]:
        print(x, '-> TUO', rev.get(x), '| TUO', x, 'notes', m.get(x))
    sys.exit()
out = {'tuo_to_dleg654_notes': m, 'dleg654_to_tuo': rev}
(Path(__file__).resolve().parent / 'cepmap.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n',
                                                              encoding='utf-8', newline='\n')
same = sum(1 for x, ks in rev.items() if ks == [x])
print('notes', notes, 'TUO articles with a note', len(m), 'D.Leg 654 articles mapped', len(rev), 'same number', same)
print('different:', {x: ks for x, ks in rev.items() if ks != [x]})
heads = []
for e in events:
    if e[1] == 'h' and e[2] not in heads:
        heads.append(e[2])
print('TUO articles without a D.Leg 654 note:', [h for h in heads if h not in m])
