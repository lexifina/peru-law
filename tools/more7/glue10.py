"""Scan the CEP base units for list items / numbered paragraphs run into a line (mid-line markers)."""
import json, re, sys
sys.path.insert(0, 'more2')
import nlaunits
s = json.load(open('more2/cep.json', encoding='utf-8'))
u = nlaunits.units(70006, '20250523', **s['nla_args'])
pat = re.compile(r'(?<=\S)\s(\d{1,3}\.-|\d{1,3}\.\d{1,2}\.?\s[A-ZÁÉÍÓÚ]|[a-zñ]\)\s|\d{1,2}\.\s[A-ZÁÉÍÓÚ])')
for k, v in u.items():
    for i, l in enumerate(v['lines']):
        for m in pat.finditer(l):
            print(k, i, repr(l[max(0, m.start() - 50):m.start() + 40]))
print(len(u), 'units')
