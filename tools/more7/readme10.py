"""README row/paragraphs and jurisdiction.json build entry for part 9g (idempotent): python -X utf8 more7/readme10.py"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / 'repo' / 'README.md'
s = P.read_text(encoding='utf-8')

ROW = ("| `codigo-ejecucion-penal/` | Texto Único Ordenado del Código de Ejecución Penal (Decreto Supremo 003-2021-JUS) | 6 | "
       "Editora Perú's consolidated text of 23 December 2024 through Leyes 32330 and 32372, Decretos Legislativos 1736 and "
       "1737 and Ley 32684 (in force 3 July 2026) |")
CHECK = ("- **Texto Único Ordenado del Código de Ejecución Penal.** The first version is Editora Perú's consolidated text, "
         "checked provision by provision against that file as above. The amending norms cite Decreto Legislativo 654 in "
         "its own numbering; each change is placed in the Texto Único Ordenado article of the same heading, by the Texto "
         "Único Ordenado's own concordance notes, with only the leading article and paragraph numbers renumbered (for "
         "example 46.1 -> 51.1). Articles they add keep their own numbers, placed after the article they follow; Ley "
         "32684's art. 37-C is numbered 40-C, following Editora Perú's notes on arts. 40-A and 40-B. Each change is the "
         "norm's own wording from El Peruano's pages. Every ley, decreto legislativo and decreto de urgencia published "
         "from 11 May 2020 to 31 October 2026 was read for the code's name.")
LIMIT = ("- **Texto Único Ordenado del Código de Ejecución Penal:** history before 23 December 2024 is not rebuilt, and the "
         "Reglamento Editora Perú prints with it is not included. A later Editora Perú consolidation has no usable text "
         "layer, so the changes of 2025 and 2026 are checked only against the norms' own text. Decreto Legislativo 1688's "
         "article, which the consolidation prints twice (as 37-A and as 40-A), is kept once, as art. 40-A, as Editora "
         "Perú's note directs. Decreto Legislativo 1736's semi-open regime applies progressively; the words are dated "
         "from the day the decree took effect.")
ES = "el Texto Único Ordenado del Código de Ejecución Penal (desde diciembre de 2024, con las Leyes 32330, 32372 y 32684 y los Decretos Legislativos 1736 y 1737)"
ANCHOR_ES = ", reconstruidos a partir de las ediciones oficiales del Ministerio de Justicia y del texto de cada ley modificatoria."

lines = s.split('\n')
if ROW not in s:
    i = max(n for n, l in enumerate(lines) if l.startswith('| `'))
    lines[i + 1:i + 1] = [ROW]
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
item = 'Texto Único Ordenado del Código de Ejecución Penal 2024-2026 (6 versions)'
if item not in j['build']:
    j['build'] = j['build'].rstrip().rstrip('.') + '; ' + item
indent = 2 if '\n  "' in raw else 1
J.write_text(json.dumps(j, ensure_ascii=False, indent=indent) + '\n', encoding='utf-8', newline='\n')
print('ok')
