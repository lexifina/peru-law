"""README rows/paragraphs and jurisdiction.json build entry for part 9i (idempotent): python -X utf8 more8/readme12.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / 'repo' / 'README.md'
s = P.read_text(encoding='utf-8')

ROWS = [
    "| `ley-general-turismo-29408/` | Ley General de Turismo (Ley 29408) | 2 | Editora Perú's consolidated text of 27 "
    "December 2023; repealed as a whole by Ley 32392 from 28 June 2025 (last version empty) |",
    "| `nueva-ley-general-turismo/` | Nueva Ley General de Turismo (Ley 32392) | 2 | the law as published in El Peruano "
    "on 27 June 2025 (in force 28 June 2025); paragraphs of art. 25 that apply from 1 January 2026 enter then |",
]
CHECK = ("- **Ley General de Turismo (Ley 29408) and Nueva Ley General de Turismo (Ley 32392).** Ley 29408's text is "
         "Editora Perú's consolidated text of 27 December 2023, checked provision by provision against that file as above; "
         "its repeal is dated from Ley 32392's own derogatory provision. Ley 32392 has no consolidation: its text is the "
         "law as published in El Peruano, read from the official PDF of the norm. Every ley, decreto legislativo and "
         "decreto de urgencia published from 20 December 2023 to 31 October 2026 was read for the laws' names; none "
         "restates words of either law.")
LIMIT = ("- **Ley General de Turismo and Nueva Ley General de Turismo:** history of Ley 29408 before 27 December 2023 is not "
         "rebuilt, and the reglamentos are not included. No Editora Perú consolidation of Ley 32392 exists, so its text is "
         "checked only against its own publication. Paragraphs 25.2.1, 25.2.2, 25.2.3 and 25.2.5 of its art. 25 apply "
         "from 1 January 2026 (its art. 26) and are shown from that day.")
ES = ("la Ley General de Turismo (Ley 29408, texto de diciembre de 2023, derogada desde el 28 de junio de 2025) y la Nueva "
      "Ley General de Turismo (Ley 32392)")
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
for item in ('Ley General de Turismo (Ley 29408) 2023-2025 (2 versions; repealed)',
             'Nueva Ley General de Turismo (Ley 32392) 2025-2026 (2 versions)'):
    if item not in j['build']:
        j['build'] = j['build'].rstrip().rstrip('.') + '; ' + item
indent = 2 if '\n  "' in raw else 1
J.write_text(json.dumps(j, ensure_ascii=False, indent=indent) + '\n', encoding='utf-8', newline='\n')
print('ok')
