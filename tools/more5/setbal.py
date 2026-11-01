"""Turn on nla_args.balanced in build_nla specs (re-apply after regenerating specs with more3/more4 generators).
    python -X utf8 more5/setbal.py more2/<spec>.json ..."""
import json
import sys
from pathlib import Path

for f in sys.argv[1:]:
    p = Path(f)
    s = json.loads(p.read_text(encoding='utf-8'))
    if s.setdefault('nla_args', {}).get('balanced'):
        continue
    s['nla_args']['balanced'] = True
    p.write_text(json.dumps(s, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('balanced on', f)
