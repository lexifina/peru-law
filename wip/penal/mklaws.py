"""Discovery helper: add to laws.json every norm the report (.tmp/report.json) found quoting or repealing articles of
the Código Penal. Existing entries (matched by op) keep their hand-set fields; new ones get the default in-force day
(the day after publication, Constitución art. 109) and "check_vigencia": true until their text is read.

    python -X utf8 penal/mklaws.py
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    rep = json.loads((HERE / '.tmp' / 'report.json').read_text(encoding='utf-8'))
    path = HERE / 'laws.json'
    spec = json.loads(path.read_text(encoding='utf-8'))
    have = {l['op'] for l in spec['laws']} | set(spec.get('not_amending', {}))
    added = 0
    for op, x in rep.items():
        if op in have or not (x.get('quotes') or x.get('repeals') or x.get('partial_repeals')):
            continue
        r = x['rec']
        n = re.sub(r'\D', '', r['numero'])
        dleg = r['tipo'].startswith('DECRETO')
        pub = r['date']
        spec['laws'].append({
            'key': ('dleg-' if dleg else 'ley-') + n,
            'label': ('Decreto Legislativo ' if dleg else 'Ley ') + n,
            'title': r['sumilla'],
            'kind': 'decree' if dleg else 'law',
            'published': pub,
            'in_force': (dt.date.fromisoformat(pub) + dt.timedelta(days=1)).isoformat(),
            'op': op, 'pdf': r['pdf'],
            'heading': ('decreto\\s+legislativo' if dleg else 'ley') + '\\s*n?\\s*[°º.]?\\s*' + n,
            'check_vigencia': True,
        })
        added += 1
    spec['laws'].sort(key=lambda l: (l['in_force'], l['published'], l['key']))
    path.write_text(json.dumps(spec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print('added', added, 'total', len(spec['laws']))


if __name__ == '__main__':
    main()
