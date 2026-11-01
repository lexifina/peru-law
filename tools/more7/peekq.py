import sys, json
from pathlib import Path
sys.path.insert(0, 'more2')
import fitz, nlaunits
spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
ps = nlaunits.paragraphs(nlaunits.rows(fitz.open(nlaunits.path(spec['nla_id'], spec['base']['capture']))))
for p in ps:
    p = ' '.join(p.split())
    i = p.find(sys.argv[2])
    if i >= 0:
        print(repr(p[max(0, i - 80):i + len(sys.argv[2]) + 60]))
print('split_at', spec.get('nla_args', {}).get('split_at'), 'base_fix keys', list(spec.get('base_fix', {})))
