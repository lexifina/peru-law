"""Print a law's paragraphs in full: python -X utf8 more2/paras.py SPEC KEY"""
import sys, json
sys.path.insert(0, 'more2'); sys.path.insert(0, 'penal')
import build_nla
S = json.load(open(sys.argv[1], encoding='utf8'))
law = next(l for l in S['laws'] if l['key'] == sys.argv[2])
ps, _ = build_nla.law_paras(law)
for i, p in enumerate(ps):
    print(i, p[:int(sys.argv[3]) if len(sys.argv) > 3 else 400])
