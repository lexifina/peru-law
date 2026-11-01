"""Add this round's acts to repo/jurisdiction.json's build string (idempotent): python -X utf8 more5/juris7.py PART..."""
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parent.parent / 'repo' / 'jurisdiction.json'
raw = P.read_text(encoding='utf-8')
j = json.loads(raw)
ADD = {
    '9a': ['Decreto Legislativo 713 de descansos remunerados 2022-2023 (5 versions)',
           'Decreto Legislativo 892 de participación en las utilidades 2021 (2 versions)',
           'Decreto Legislativo 688 de Consolidación de Beneficios Sociales 2023 (1 version)'],
    '9b': ['Ley 28518 sobre Modalidades Formativas Laborales 2020 (1 version)',
           'Ley 26644 de descanso prenatal y postnatal 2022 (1 version)',
           'Decreto Legislativo 1405 de descanso vacacional 2020 (1 version)'],
    '9c': ['Ley 27908 de Rondas Campesinas 2022 (1 version)',
           'Ley 30403 que prohíbe el castigo físico y humillante 2022 (1 version)',
           'Ley 26856 de playas del litoral 2020 (1 version)'],
    '9d': ['Ley 29245 de tercerización 2021 (1 version)',
           'Ley 27133 de promoción de la industria del gas natural 2022 (1 version)'],
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
