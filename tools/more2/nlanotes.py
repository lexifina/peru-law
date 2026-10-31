"""List the amendment notes of an NLA capture: (law, date) counts, notes with publication dates on/after FROM.
    python -X utf8 more2/nlanotes.py ID TS [FROM YYYY]"""
import sys, re, hashlib, collections
from pathlib import Path
import fitz
fitz.TOOLS.mupdf_display_errors(False)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'penal')); sys.path.insert(0, str(HERE.parent))
import nla
C = HERE.parent / '.cache'
U = 'https://web.archive.org/web/{ts}id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma={id}'
i, ts = sys.argv[1], sys.argv[2]
since = int(sys.argv[3]) if len(sys.argv) > 3 else 0
d = fitz.open(str(C / hashlib.sha256(U.format(id=i, ts=ts).encode()).hexdigest()))
runs = nla.stream(d)
notes = ' '.join(t for t, n in runs if n)
notes = ' '.join(notes.split())
MES = 'enero febrero marzo abril mayo junio julio agosto setiembre septiembre octubre noviembre diciembre'.split()
c = collections.Counter()
for m in re.finditer(r'((?:Ley|Decreto Legislativo|Decreto de Urgencia|Resoluci[óo]n Legislativa)\s+N[°º]\s*[\d-]+[^,]{0,10}),?\s+publicad[oa] el (\d+) de (\w+) (?:del? )?(\d{4})', notes):
    y = int(m.group(4))
    if y >= since:
        c[(m.group(1).strip(), '%s-%02d-%02d' % (y, MES.index(m.group(3).lower()) + 1 if m.group(3).lower() in MES else 0, int(m.group(2))))] += 1
for (law, dt), n in sorted(c.items(), key=lambda x: x[0][1]):
    print(dt, law, n)
