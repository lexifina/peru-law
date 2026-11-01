"""Unit lines that hold another heading inside them (a missed paragraph break): python -X utf8 more8/glue11.py SPEC.json"""
import json, re, sys
sys.path.insert(0, 'more2')
import nlaunits
s = json.load(open(sys.argv[1], encoding='utf-8'))
u = nlaunits.units(s['nla_id'], s['base']['capture'], **s['nla_args'])
RX = re.compile(r'(?<=[.;:”])\s+[“"]?(?:Art[íi]culo\s+\d+[-A-Z ]*\.?-|(?:Primer|Segund|Tercer|Cuart|Quint|Sext|S[ée]ptim|S[ée]tim|Octav|Noven|D[ée]cim|Und[ée]cim|Duod[ée]cim|Vig[ée]sim)[oa]?(?:\s+[A-Z][a-zé]+)?\s*\.-|[a-zñ]\)\s|\d{1,2}\.\d{0,2}\.?\s[A-ZÁÉÍÓÚ]|\d{1,2}\)\s)')
for k, v in u.items():
    for i, l in enumerate(v['lines']):
        for m in RX.finditer(l):
            print(k, i, '...' + l[max(0, m.start() - 50):m.end() + 40])
