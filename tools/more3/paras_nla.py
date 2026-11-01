"""Print the paragraphs of an NLA capture (debugging): python -X utf8 more3/paras_nla.py ID TS [FROM [TO]] [grep=REGEX]"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'more2'))
import fitz, nlaunits
args = [a for a in sys.argv[1:] if not a.startswith('grep=')]
g = [a[5:] for a in sys.argv[1:] if a.startswith('grep=')]
ps = nlaunits.paragraphs(nlaunits.rows(fitz.open(str(nlaunits.path(args[0], args[1])))), True)
a = int(args[2]) if len(args) > 2 else 0
b = int(args[3]) if len(args) > 3 else len(ps)
for i, p in enumerate(ps[a:b], a):
    if not g or re.search(g[0], p):
        print(i, p[:150])
