"""Discovery only: for every norm the El Peruano scan found naming the Código Penal (.tmp/scan.jsonl), cut the
norm's own text and list what it does to the Code (quoted articles, repeals, notes). Writes .tmp/report.json.

    python -X utf8 penal/report.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fetch  # noqa: E402
import forward  # noqa: E402
import lawtext  # noqa: E402


def heading_re(rec) -> str:
    n = re.sub(r'\D', '', rec['numero'])
    t = 'decreto\\s+legislativo' if rec['tipo'].startswith('DECRETO') else 'ley'
    return t + r'\s*n?\s*[°º.]?\s*' + n


def main():
    recs = {}
    for l in (HERE / '.tmp' / 'scan.jsonl').read_text(encoding='utf-8').splitlines():
        r = json.loads(l)
        if r.get('nhits'):
            recs[r['op']] = r
    out = {}
    for op, r in sorted(recs.items(), key=lambda kv: (kv[1]['date'] or '', kv[0])):
        p = fetch.cached(r['pdf'])
        if p is None:
            continue
        try:
            paras = lawtext.paragraphs(p, op, heading_re(r))
        except SystemExit as e:
            out[op] = {'rec': r, 'error': str(e)}
            print(r['numero'], r['date'], 'ERROR', e, flush=True)
            continue
        q, notes = forward.cp_quotes(paras)
        rep, part = forward.cp_repeals(paras)
        mentions = [p[:200] for p in paras if forward.CP.search(p) and not re.search(
            r'(?:Procesal|Procedimientos|Ejecuci[óo]n|Responsabilidad)\s+Penal', p, re.I)]
        out[op] = {'rec': r, 'quotes': [(k, len(ps), any(forward.ELL.match(x) for x in ps)) for k, ps, _ in q],
                   'notes': notes, 'repeals': rep, 'partial_repeals': part,
                   'vigencia': [p[:300] for p in paras if re.search(r'vigencia|vigor', p, re.I)],
                   'mentions': mentions[:6]}
        if q or rep or part:
            print(r['tipo'][:3], r['numero'], r['date'], [k for k, _, _ in q], 'rep', rep, 'part', len(part),
                  'notes', len(notes), flush=True)
    (HERE / '.tmp' / 'report.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
