"""Numbering map Ley 27444 -> TUO (DS 004-2019-JUS) from the TUO's own concordance notes ("(Texto según el artículo N
de la Ley Nº 27444 ...)") in Editora Perú's file: each note's article -> the TUO unit and the paragraph it follows.
    python -X utf8 more4/lpagmap.py [ART ...]     (no ART: write more4/lpagmap.json)"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'more2'))
import nlaunits  # noqa: E402
A = {"sumillas": True, "bold_breaks": True, "fn_markers": True, "ord_heads2": True, "caps_heads": True, "sec_first": True,
     "end_marker": "^(?:Tabla de Contenido|ANEXO)"}
us = nlaunits.units(12, '20250411', **A)
NOTE = re.compile(r'\((?:Texto|P[áa]rrafo|Numeral|Art[íi]culo)[^()]*?según\s+(?:el|la|los)\s+(?:art[íi]culo|numeral|literal|'
                  r'p[áa]rrafo)s?\s+([IVX]+|\d+(?:-[A-Z])?)[^()]*?Ley\s+N[°º]\s*27444[^()]*\)')
m = {}
for k, u in us.items():
    for i, l in enumerate(u['lines']):
        for n in NOTE.finditer(l):
            m.setdefault(n.group(1), []).append({'tuo': k, 'line': i, 'para': l[:n.start()].strip()[:90], 'note': n.group(0)[:160]})
if sys.argv[1:]:
    for a in sys.argv[1:]:
        for x in m.get(a, []):
            print(a, '->', x['tuo'], 'line', x['line'], '|', x['para'], '|', x['note'])
else:
    (HERE / 'lpagmap.json').write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(m), 'Ley 27444 articles mapped')
