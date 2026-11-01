import sys, re, hashlib
from pathlib import Path
import fitz
fitz.TOOLS.mupdf_display_errors(False)
C = Path(__file__).resolve().parent.parent / '.cache'
U = 'https://web.archive.org/web/{ts}id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma={id}'
for a in sys.argv[1:]:
    i, ts = a.split(':')
    p = C / hashlib.sha256(U.format(id=i, ts=ts).encode()).hexdigest()
    if not p.exists(): print(a, 'missing'); continue
    try: d = fitz.open(str(p))
    except Exception as e: print(a, 'ERR'); continue
    txt = ''.join(pg.get_text() for pg in d)
    first = ' '.join(''.join(pg.get_text() for pg in d[:3]).split())[:150]
    m = re.search(r'ACTUALIZAD[AO]\s+(\d\d/\d\d/\d{4})', txt)
    print(a, 'pages', d.page_count, 'chars', len(txt), 'upd', m.group(1) if m else '-', 'mod', (d.metadata.get('modDate') or '')[2:10], '|', first)
