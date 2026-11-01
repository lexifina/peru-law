"""Add this round's acts to repo/jurisdiction.json's build string (idempotent): python -X utf8 more6/juris8.py PART..."""
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parent.parent / 'repo' / 'jurisdiction.json'
raw = P.read_text(encoding='utf-8')
j = json.loads(raw)
ADD = {
    '9e': ['Decreto Legislativo 1186 sobre el uso de la fuerza policial 2022-2025 (2 versions)',
           'Ley 25129 de asignación familiar 2022 (2 versions)'],
    '9f': ['Texto Único Ordenado de la Ley de Tributación Municipal 2022-2027 (5 versions, 1 future)'],
}
b = j['build']
for part in sys.argv[1:]:
    for item in ADD[part]:
        if item not in b:
            b = b.rstrip().rstrip('.') + '; ' + item
j['build'] = b
indent = 2 if '\n  "' in raw else 1
P.write_text(json.dumps(j, ensure_ascii=False, indent=indent) + '\n', encoding='utf-8', newline='\n')
print(b[-400:])
