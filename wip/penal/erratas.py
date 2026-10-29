"""Discovery: El Peruano's "FE DE ERRATA" notices for each norm in laws.json, published within 60 days after it.

    python -X utf8 penal/erratas.py        -> .tmp/erratas_found.json and a printed list

A fe de erratas reprints a passage as published ("DICE") and as it should read ("DEBE DECIR"). Those that touch the
Code's wording become their own entries in laws.json (key "<law key>-fe-erratas").
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import elperuano  # noqa: E402


def main():
    spec = json.loads((HERE / 'laws.json').read_text(encoding='utf-8'))
    found = {}
    for law in spec['laws']:
        if law['key'].endswith('-fe-erratas'):
            continue
        n = re.search(r'(\d{3,5}(?:-\d{4})?)$', law['label']).group(1)
        a = dt.date.fromisoformat(law['published'])
        b = a + dt.timedelta(days=60)
        f = lambda d: d.strftime('%Y%m%d')  # noqa: E731
        items = elperuano.items_both(f(a), f(b), 'FE DE ERRATA')
        hits = [it for it in items if re.search(r'\b%s\b' % re.escape(n), it['numero'])]
        if hits:
            found[law['key']] = hits
            for it in hits:
                print(law['key'], it['numero'], it['date'], it['op'], it['pdf'], flush=True)
    (HERE / '.tmp' / 'erratas_found.json').write_text(json.dumps(found, ensure_ascii=False, indent=1),
                                                      encoding='utf-8')


if __name__ == '__main__':
    main()
