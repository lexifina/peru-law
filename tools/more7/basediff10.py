"""Compare the CEP base units with and without the spec's split_at (which units the split changes)."""
import json, sys
sys.path.insert(0, 'more2')
import nlaunits
s = json.load(open('more2/cep.json', encoding='utf-8'))
a = s['nla_args']
u1 = nlaunits.units(70006, '20250523', **a)
u0 = nlaunits.units(70006, '20250523', **{k: v for k, v in a.items() if k != 'split_at'})
print(len(u0), len(u1), sorted(set(u0) ^ set(u1)))
for k in u1:
    if k in u0 and u0[k]['lines'] != u1[k]['lines']:
        print('CHANGED', k, len(u0[k]['lines']), '->', len(u1[k]['lines']))
        if ''.join(u0[k]['lines']).replace(' ', '') != ''.join(u1[k]['lines']).replace(' ', ''):
            print('   WORDS DIFFER')
if len(sys.argv) > 1:
    for k in sys.argv[1:]:
        print('==', k)
        for l in u0.get(k, {}).get('lines', []):
            print(' 0|', l[:150])
        for l in u1.get(k, {}).get('lines', []):
            print(' 1|', l[:150])
