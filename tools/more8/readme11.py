"""README rows/paragraphs and jurisdiction.json build entry for part 9h (idempotent): python -X utf8 more8/readme11.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / 'repo' / 'README.md'
s = P.read_text(encoding='utf-8')

ROWS = [
    "| `decreto-ley-sistema-nacional-pensiones/` | Decreto Ley que crea el Sistema Nacional de Pensiones de la Seguridad "
    "Social (Decreto Ley 19990) | 1 | Editora Perú's consolidated text of 25 October 2021 |",
    "| `ley-sistema-privado-pensiones/` | Texto Único Ordenado de la Ley del Sistema Privado de Administración de Fondos de "
    "Pensiones (Decreto Supremo 054-97-EF) | 4 | Editora Perú's consolidated text of 3 May 2023 through Leyes 32428, 32123 "
    "(in force 6 September 2025) and 32445 |",
]
CHECK = ("- **Decreto Ley 19990 and the Texto Único Ordenado de la Ley del Sistema Privado de Pensiones.** Each first version "
         "is Editora Perú's consolidated text, checked provision by provision against that file as above. The changes to "
         "the Texto Único Ordenado are the amending laws' own wording from El Peruano's pages; Ley 32123's changes date "
         "from 6 September 2025, the day after its reglamento (Decreto Supremo 189-2025-EF) was published, as the law "
         "provides. Every ley, decreto legislativo and decreto de urgencia published from 11 May 2020 to 31 October 2026 "
         "was read for the laws' names; none restates words of Decreto Ley 19990.")
LIMIT = ("- **Decreto Ley 19990 and the Texto Único Ordenado de la Ley del Sistema Privado de Pensiones:** history before "
         "25 October 2021 and 3 May 2023 is not rebuilt, and the reglamentos Editora Perú prints with them are not "
         "included. Later Editora Perú consolidations have no usable text layer, so Decreto Ley 19990 is not compared with "
         "a second consolidation and the 2025 changes to the Texto Único Ordenado are checked only against the laws' own "
         "text. In art. 8 of the Texto Único Ordenado, Ley 27617's wording of the second and third paragraphs takes "
         "effect only once a restructuring of the Sistema Nacional de Pensiones is carried out, a condition with no date, "
         "so the earlier wording is shown. The rules of Ley 32123 that stand in its own articles (the Sistema Integral "
         "Previsional) are not part of either text.")
ES = ("el Decreto Ley 19990 del Sistema Nacional de Pensiones (texto de octubre de 2021) y el Texto Único Ordenado de la "
      "Ley del Sistema Privado de Pensiones (desde mayo de 2023, con las Leyes 32428, 32123 y 32445)")
ANCHOR_ES = ", reconstruidos a partir de las ediciones oficiales del Ministerio de Justicia y del texto de cada ley modificatoria."

lines = s.split('\n')
for row in ROWS:
    if row not in '\n'.join(lines):
        i = max(n for n, l in enumerate(lines) if l.startswith('| `'))
        lines[i + 1:i + 1] = [row]
s = '\n'.join(lines)
for text, sec in ((CHECK, '## How it is checked'), (LIMIT, '## What it does not show')):
    if text in s:
        continue
    lines = s.split('\n')
    i = [n for n, l in enumerate(lines) if l.startswith(sec)][0]
    k = [n for n, l in enumerate(lines) if n > i and l.startswith('## ')][0]
    while not lines[k - 1].strip():
        k -= 1
    lines.insert(k, text)
    s = '\n'.join(lines)
if ES not in s:
    assert s.count(ANCHOR_ES) == 1
    s = s.replace(ANCHOR_ES, ', ' + ES + ANCHOR_ES)
P.write_text(s, encoding='utf-8', newline='\n')

J = ROOT / 'repo' / 'jurisdiction.json'
raw = J.read_text(encoding='utf-8')
j = json.loads(raw)
for item in ('Decreto Ley 19990 del Sistema Nacional de Pensiones 2021 (1 version)',
             'Texto Único Ordenado de la Ley del Sistema Privado de Pensiones 2023-2025 (4 versions)'):
    if item not in j['build']:
        j['build'] = j['build'].rstrip().rstrip('.') + '; ' + item
indent = 2 if '\n  "' in raw else 1
J.write_text(json.dumps(j, ensure_ascii=False, indent=indent) + '\n', encoding='utf-8', newline='\n')
print('ok')
