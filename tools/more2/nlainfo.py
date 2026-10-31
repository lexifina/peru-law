import sys, re, hashlib
from pathlib import Path
import fitz
fitz.TOOLS.mupdf_display_errors(False)
C = Path(__file__).resolve().parent.parent / '.cache'
U = 'https://web.archive.org/web/{ts}id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma={id}'
for a in sys.argv[1:]:
    i, ts = a.split(':')
    p = C / hashlib.sha256(U.format(id=i, ts=ts).encode()).hexdigest()
    try:
        d = fitz.open(str(p))
    except Exception as e:
        print(a, 'ERR', e); continue
    t = d[0].get_text() if d.page_count else ''
    full = ''.join(pg.get_text() for pg in d)
    print(a, 'pages', d.page_count, 'fffd', full.count('�'), 'mod', d.metadata.get('modDate'))
    print('   ', ' '.join(t.split())[:400])
    print('   dates:', sorted(set(re.findall(r'[Aa]ctualizad[oa][^\n]{0,40}', full)))[:3])
