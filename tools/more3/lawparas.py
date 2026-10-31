"""Print a law's paragraphs as build_nla cuts them:  python -X utf8 more3/lawparas.py PDF OP HEADING [WIDTH] [grep=RE]"""
import sys, re
sys.path.insert(0, 'more2'); sys.path.insert(0, 'penal')
import build_nla
a = [x for x in sys.argv[1:] if not x.startswith('grep=')]
g = [x[5:] for x in sys.argv[1:] if x.startswith('grep=')]
ps, sha = build_nla.law_paras({'pdf': a[0], 'op': a[1], 'heading': a[2]})
w = int(a[3]) if len(a) > 3 else 300
for i, p in enumerate(ps):
    if not g or re.search(g[0], p):
        print(i, p[:w])
