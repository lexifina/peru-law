"""Build corpus.d/60-proc.json: the Código Procesal Penal (Decreto Legislativo 957) with its history.

Reads only the cache (../.cache). Deterministic. Writes atomically.

    python -X utf8 proc/parse_proc.py            write ../corpus.d/60-proc.json
    python -X utf8 proc/parse_proc.py --report   print problems, the law table and the checkpoints
    python -X utf8 proc/parse_proc.py --out P    write elsewhere (testing)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fetch  # noqa: E402
import edition  # noqa: E402
import history  # noqa: E402
from history import Problem, calls_in, classify, strip_calls, vigencia  # noqa: E402

ED8 = ('https://cdn.www.gob.pe/uploads/document/file/7451652/'
       '6346160-codigo-procesal-penal-decreto-legislativo-final.pdf?v=1735938504')
ED8_PAGES = (21, 385)
ED8_DATE = '2024-11-17'    # "La presente edición se encuentra actualizada hasta el 17 de noviembre de 2024" (p. 13)
ED8_PAGE = 'https://www.gob.pe/institucion/minjus/informes-publicaciones/6346160-codigo-procesal-penal-octava-edicion-oficial-actualizada-a-noviembre-de-2024'
MAPA = 'https://cdn.www.gob.pe/uploads/document/file/2107657/MAPA%202021.pdf.pdf?v=1629490576'
PUBLISHED = '2004-07-29'
D0 = '2004-07-30'           # Constitución art. 109: binding from the day after publication

OUT = HERE.parent / 'corpus.d' / '60-proc.json'


def text_of(paras: list[str]) -> str:
    return ''.join(strip_calls(p).rstrip() + '\n' for p in paras)


def load(url, pages):
    path = fetch.cached(url)
    if path is None:
        raise SystemExit(f'not in the cache: {url} (run proc/pfetch.py --plan)')
    body, notes = edition.read(str(path), *pages)
    units, struct = edition.units(body)
    trees = {str(n): edition.note_tree(ls, str(n)) for n, ls in notes.items()}
    return path, units, struct, trees


def law_table(trees: dict, log: list[str]):
    """law key -> {label, published, in_force, how}. A note that states the law's own start wins; otherwise the
    Constitution's rule (the day after publication)."""
    laws: dict[str, dict] = {}
    for t in trees.values():
        for ev in history.all_events(t):
            if not ev.law:
                continue
            key, label = ev.law
            L = laws.setdefault(key, {'label': label, 'published': set(), 'stated': {}})
            if ev.published:
                L['published'].add(ev.published)
            d, how = vigencia(ev.note.header, ev.published)
            if how:
                L['stated'].setdefault(d, how)
    out = {}
    for key, L in laws.items():
        pubs = sorted(L['published'])
        if len(pubs) > 1:
            log.append(f'law {key}: notes give several publication days {pubs}; using the earliest')
        pub = pubs[0] if pubs else None
        stated = {d: h for d, h in L['stated'].items() if d}
        if key in OVERRIDE:
            d, how = OVERRIDE[key]
        elif len(stated) == 1:
            d, how = next(iter(stated.items()))
        elif len(stated) > 1:
            log.append(f'law {key}: notes state several start days {stated}; using the latest')
            d = max(stated)
            how = stated[d]
        elif pub:
            d, how = history.plus(pub, days=1), 'default: the day after publication (Constitución art. 109)'
        else:
            d, how = None, None
        if any(not dd for dd in L['stated']):
            log.append(f'law {key}: a note ties its start to an event the source does not date: {L["stated"].get(None)}')
        out[key] = {'label': L['label'], 'published': pub, 'in_force': d, 'how': how}
    return out


# Start days the notes do not give by themselves, with where they come from.
OVERRIDE: dict[str, tuple[str, str]] = {}


def build(report: bool = False):
    log: list[str] = []
    path, units, struct, trees = load(ED8, ED8_PAGES)
    owner: dict[str, str] = {}
    for u in units:
        for p in u['paras']:
            for c in calls_in(p):
                owner[c] = u['key']
    for s, i in struct:
        for c in calls_in(s):
            owner[c] = 'estructura'
    for n in trees:
        if n not in owner:
            log.append(f'note {n} has no call in the body')
    laws = law_table(trees, log)

    def indate(ev):
        return laws[ev.law[0]]['in_force'] if ev.law else None

    problems = []
    timelines = {}
    commence = []
    for u in units:
        mine = {n: trees[n] for n in sorted(trees, key=int) if owner.get(n) == u['key']}
        try:
            orig, states, others = history.rewind(u['paras'], mine, indate, log, u['key'])
        except Problem as e:
            problems.append(str(e))
            continue
        timelines[u['key']] = (orig, states)
        for ev in others:
            if ev.kind == 'commence':
                commence.append((u['key'], ev))
    if report:
        print('PROBLEMS', len(problems))
        for p in problems:
            print('  ', p)
        print('LOG', len(log))
        for l in log:
            print('  ', l)
    return locals()


if __name__ == '__main__':
    r = build(report='--report' in sys.argv)
