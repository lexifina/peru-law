"""Quality checks of an NLA parse: python -X utf8 more3/qa.py SPEC TS"""
import sys, re, json; sys.path.insert(0, 'more2')
import nlaunits
s = json.load(open(sys.argv[1], encoding='utf8'))
u = nlaunits.units(s['nla_id'], sys.argv[2], **s.get('nla_args', {}))
print(len(u), 'units')
arts = [k for k in u if k.startswith('art-')]
nums = sorted({int(k[4:7]) for k in arts})
gaps = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
print('art range', nums[0], nums[-1], 'missing numbers', gaps[:80])
for k, x in u.items():
    if not k.startswith('art'):
        print(k, x['label'], '|', x['lines'][0][:70], '|', len(x['lines']))
for k, x in u.items():
    ls = x['lines']
    if len(ls) < 2 or not ls[-1].rstrip().endswith(('.', ':', ';', '”', '"')):
        print('END?', k, repr(ls[-1][-80:]))
    for l in ls:
        if re.search(r'NORMAS LEGALES|Tabla de Contenido|Editora Per|\(\*\)|publicad[ao] el \d|^Inicio|¿DESEAS', l):
            print('SUSPECT', k, l[:160])
        if re.match(r'^(LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|SUBCAP)', l):
            print('STRUCT?', k, l[:120])
