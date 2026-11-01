"""Print the first N chars of a cached NLA capture: python -X utf8 more6/head.py ID TS [N] [OFFSET]"""
import sys, hashlib
from pathlib import Path
import fitz
fitz.TOOLS.mupdf_display_errors(False)
C = Path(__file__).resolve().parent.parent / '.cache'
U = 'https://web.archive.org/web/{ts}id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma={id}'
i, ts = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
o = int(sys.argv[4]) if len(sys.argv) > 4 else 0
d = fitz.open(str(C / hashlib.sha256(U.format(id=i, ts=ts).encode()).hexdigest()))
t = ''.join(p.get_text() for p in d)
print(t[o:o + n])
