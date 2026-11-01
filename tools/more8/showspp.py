"""Print each later version's changed units of .tmp/p7/spp.json (and the base text of the same keys)."""
import json
p = json.load(open('.tmp/p7/spp.json', encoding='utf-8'))
v = p['acts'][0]['versions']
base = v[0]['units']
for x in v[1:]:
    print('########', x['from'], x['credits'] and list(x['credits'].values())[0])
    for k, u in x['changes'].items():
        print('==', k, '|', u['label'] if u else None)
        if k in base:
            print('  BASE:', base[k]['text'].replace('\n', '\n        ')[:3000])
        print('  NEW: ', u['text'].replace('\n', '\n        ') if u else None)
