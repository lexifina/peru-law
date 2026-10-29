"""Código Penal part: corpus.d/80-penal.json.

    python -X utf8 penal/parse_penal.py            write the part (atomically) and print the checkpoints
    PE_DIFF=1 ...                                  also print every checkpoint difference

History:
  1. The Code as printed in the Ministry of Justice's twelfth official edition (current to 31 May 2016), credited to
     the publisher as the oldest version available (penal/base.py).
  2. Every later change from the amending norm's own El Peruano text (penal/lawtext.py, penal/forward.py), in the
     order of laws.json, which lists each norm with its operation number, PDF, publication and in-force days.
  3. Checkpoints: the rebuilt text on a day is compared word for word with Editora Perú's Normas Legales
     Actualizadas of that day (penal/nla.py, penal/compare.py). Differences are printed; explained ones are listed in
     laws.json "explained" and in the part's decisions.

Reads only the cache (../.cache). Deterministic.
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
import base  # noqa: E402
import compare  # noqa: E402
import fetch  # noqa: E402
import forward  # noqa: E402
import lawtext  # noqa: E402
import nla  # noqa: E402
from edition import clean_par, label_of  # noqa: E402
from base import HEAD as BHEAD  # noqa: E402

PART = HERE.parent / 'corpus.d' / '80-penal.json'
SLUG = 'codigo-penal'


def unit(key: str, paras: list[str], old: dict | None) -> dict:
    paras = [clean_par(p) for p in paras if p.strip()]
    return {'label': (old or {}).get('label') or forward.art_label(key), 'kind': (old or {}).get('kind') or 'art',
            'text': ''.join(p + '\n' for p in paras)}


def law_paras(law: dict) -> tuple[list[str], Path]:
    p = fetch.cached(law['pdf'])
    if p is None:
        raise SystemExit(f'not in the cache: {law["pdf"]}')
    return lawtext.paragraphs(p, law['op'], law['heading']), p


def _flat(paras):
    return ' '.join(' '.join(clean_par(p) for p in paras).split())


def apply_law(law: dict, state: dict, log: list[str]) -> dict:
    paras, path = law_paras(law)
    changes: dict[str, dict | None] = {}
    if law.get('ops') is not None:
        quotes = []
        allq, _ = forward.cp_quotes(paras, every=bool(law.get('every_quote')))
        byk = {}
        for k, ps, h in allq:
            byk.setdefault(k, []).append((ps, h))
        ops = law['ops']
    else:
        allq, notes = forward.cp_quotes(paras)
        rep, part = forward.cp_repeals(paras)
        if part and not law.get('partial_ok'):
            raise SystemExit(f'{law["key"]}: partial repeal needs hand operations: {part}')
        ops = [['quote', k, i] for i, (k, _, _) in enumerate(allq) if k not in law.get('skip', [])] + \
            [['repeal', k] for k in rep if k not in law.get('skip', [])]
        byk = None
    carried: set[str] = set()
    for op in ops + law.get('extra_ops', []):
        kind, key = op[0], op[1]
        cur = changes[key] if key in changes else state.get(key)
        if kind == 'quote':
            if byk is None:
                ps, intro = allq[op[2]][1], allq[op[2]][2]
            else:
                ps, intro = byk[key][op[2] if len(op) > 2 else 0]
            if any(forward.ELL.match(p) for p in ps):
                if cur is None:
                    raise SystemExit(f'{law["key"]}: partial quote of {key}, which does not exist')
                curp = [l for l in cur['text'].split('\n') if l]
                hint = forward.paragraph_hint(intro, key)
                if hint:
                    log.append(f'  {law["key"]} {key}: operative sentence: {hint}')
                new, warn = forward.merge(curp, [clean_par(p) for p in ps], hint)
                for w in warn:
                    log.append(f'  {law["key"]} {key}: {w}')
            else:
                new = ps
            changes[key] = unit(key, new, cur)
        elif kind == 'compose':
            # ['compose', key, quote index (or [key, index] in ops mode), [["q", i] | ["c", prefix], ...]]:
            # the article rebuilt by hand from quoted paragraph i and current paragraphs that start with prefix
            if byk is None:
                ps = allq[op[2]][1]
            else:
                ps = byk[key][op[2]][0]
            ps = [clean_par(p) for p in ps]
            curp = [l for l in cur['text'].split('\n') if l]
            new = []
            for what, arg in op[3]:
                if what == 'q':
                    new.append(ps[arg])
                else:
                    hit = [p for p in curp if p.startswith(arg)]
                    if len(hit) != 1:
                        raise SystemExit(f'{law["key"]} compose {key}: {arg!r} matches {len(hit)}')
                    new.append(hit[0])
            changes[key] = unit(key, new, cur)
            carried.update(p for p in new if p in curp)
        elif kind == 'repeal':
            changes[key] = None
        elif kind == 'move':               # ['move', old key, new key]: renumbered "sin alterar la literalidad";
            new_key = op[2]                # the new heading as quoted, the body as it stood
            old = changes[key] if key in changes else state.get(key)
            if old is None:
                raise SystemExit(f'{law["key"]}: move of missing {key}')
            q = byk[new_key][0][0]
            head = []
            for p in q:
                if forward.ELL.match(p):
                    break
                head.append(p)
            # a chapter title quoted just before the heading ("Capítulo I / Trata de personas") is not the article's
            hq = next((i for i, p in enumerate(head) if forward.QHEAD.match(p)), 0)
            head = head[hq:]
            curp = [l for l in old['text'].split('\n') if l]
            hi = next(i for i, p in enumerate(curp) if BHEAD.match(p))
            first = curp[hi]
            m = BHEAD.match(first)
            rest = first[m.end():].strip()
            body = ([rest] if forward.has_body(rest) else []) + curp[hi + 1:]
            changes[key] = None
            changes[new_key] = unit(new_key, head + body, None)
            carried.update(clean_par(p) for p in body)
        elif kind == 'drop_nth':           # ['drop_nth', key, n]: "Derógase el segundo párrafo del artículo 52"
            curp = [l for l in cur['text'].split('\n') if l]
            hi = next(i for i, p in enumerate(curp) if BHEAD.match(p))
            body = [i for i in range(hi + 1, len(curp)) if label_of(curp[i]) is None]
            first = curp[hi][BHEAD.match(curp[hi]).end():].strip()
            if forward.has_body(first):
                body = [hi] + body       # the heading line carries the first paragraph
            if body[op[2] - 1] == hi:
                raise SystemExit(f'{law["key"]}: drop_nth would drop the heading line')
            del curp[body[op[2] - 1]]
            changes[key] = unit(key, curp, cur)
        elif kind == 'drop_par':           # ['drop_par', key, label or paragraph prefix]
            curp = [l for l in cur['text'].split('\n') if l]
            hit = [i for i, p in enumerate(curp) if p.startswith(op[2])]
            if len(op) > 3:              # the n-th paragraph with that start ("7." of the first list)
                hit = hit[op[3] - 1:op[3]]
            if len(hit) != 1:
                raise SystemExit(f'{law["key"]}: drop_par {op} matches {len(hit)}')
            del curp[hit[0]]
            changes[key] = unit(key, curp, cur)
        else:
            raise SystemExit(f'{law["key"]}: unknown op {op}')
    # every new paragraph must occur word for word in the law's text
    flat = _flat(paras)
    fw = ' '.join(re.findall(r'\w+', flat.lower()))
    for key, u in changes.items():
        if u is None:
            continue
        old = (state.get(key) or {}).get('text', '')
        for p in u['text'].split('\n'):
            if not p or p + '\n' in old or p in carried:
                continue
            pw = ' '.join(re.findall(r'\w+', p.lower()))
            if pw not in fw:
                raise SystemExit(f'{law["key"]} {key}: paragraph not found word for word in the law: {p[:120]}')
    for key, u in changes.items():
        if u is None:
            state.pop(key, None)
        else:
            state[key] = u
    return {'changes': changes, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def derived_decisions(spec: dict, results: dict) -> list[str]:
    """One sentence per hand decision recorded in laws.json, in law order, then the checkpoint explanations."""
    out = ['Código Penal: ' + v for v in spec['base'].get('drop', {}).values()]
    if spec.get('checkpoint_rule'):
        out.append('Código Penal checkpoints: ' + spec['checkpoint_rule'])
    for law in sorted(spec['laws'], key=lambda l: (l['in_force'], l['published'], l['key'])):
        if law.get('pending'):
            out.append(f'Código Penal: {law["label"]} is not applied: {law["pending"]}')
        if law.get('vigencia'):
            out.append(f'Código Penal: {law["label"]} is in force on {law["in_force"]}: {law["vigencia"]}')
        if law.get('hand'):
            out.append(f'Código Penal: {law["label"]}: {law["hand"]}')
        if law.get('source_note'):
            out.append(f'Código Penal: {law["label"]}: {law["source_note"]}')
    for c in sorted(spec['checkpoints'], key=lambda c: c['date']):
        r = results.get(c['id'], [])
        expl = spec.get('explained', {}).get(c['id'], {})
        out.append(f'Código Penal checkpoint {c["id"]}: the rebuilt text on {c["date"]} compared word for word with '
                   f'Editora Perú\'s Normas Legales Actualizadas (Internet Archive capture {c["capture"]}): '
                   f'{len(r)} differences, each explained below.' if r else
                   f'Código Penal checkpoint {c["id"]}: the rebuilt text on {c["date"]} equals Editora Perú\'s Normas '
                   f'Legales Actualizadas (capture {c["capture"]}) word for word.')
        for k, w, d in r:
            why = expl.get(f'{k} {w}') or expl.get(k)
            out.append(f'Código Penal checkpoint {c["id"]}, {k} ({w}): {why or "UNEXPLAINED"}')
    return out


def checkpoint(state: dict, ts: str) -> list:
    p = fetch.path_for(nla.url(ts))
    return compare.compare(state, nla.segments(p))


def main():
    spec = json.loads((HERE / 'laws.json').read_text(encoding='utf-8'))
    bpath = fetch.path_for(base.URL)
    state = base.units(bpath)
    for k in spec['base'].get('drop', {}):     # printed before its law took effect (coordinator rule, 2026-10-28)
        del state[k]
    # word forms of the 2016 edition decide whether a hyphen at a line end in a law is part of the word
    lawtext.VOCAB.update(w for u in state.values() for w in re.findall(r'\w+(?:-\w+)*', u['text'].lower()))
    v0 = {'from': spec['base']['from'], 'source_url': base.URL,
          'sha256': hashlib.sha256(bpath.read_bytes()).hexdigest(),
          'units': {k: state[k] for k in sorted(state)}, 'credits': {}, 'note': spec['base']['note']}
    versions = [v0]
    laws = {}
    log: list[str] = []
    cps = sorted(spec['checkpoints'], key=lambda c: c['date'])
    results = {}
    prev_day = v0['from']
    until = os.environ.get('PE_UNTIL')          # debugging: stop the replay after this day
    for law in sorted(spec['laws'], key=lambda l: (l['in_force'], l['published'], l['key'])):
        if until and law['in_force'] > until:
            cps = [c for c in cps if c['date'] <= until]
            break
        if law.get('pending'):          # not in force on the docs date (e.g. waits for a reglamento)
            log.append(f'{law["key"]}: NOT APPLIED: {law["pending"]}')
            continue
        for c in cps:
            if c['id'] not in results and prev_day <= c['date'] < law['in_force']:
                results[c['id']] = checkpoint(state, c['capture'])
        r = apply_law(law, state, log)
        if not r['changes']:
            log.append(f'{law["key"]}: no change to the Code')
            continue
        v = {'from': law['in_force'], 'source_url': law['pdf'], 'sha256': r['sha256'],
             'changes': {k: r['changes'][k] for k in sorted(r['changes'])},
             'credits': {k: [law['key']] for k in sorted(r['changes'])},
             'note': law.get('vnote') or f'Wording of {law["label"]} from its El Peruano text ({law["pdf"]}).'}
        if versions[-1]['from'] == law['in_force']:
            v['same_day'] = True
        versions.append(v)
        laws[law['key']] = {'label': law['label'], 'title': law['title'], 'kind': law['kind'],
                            'enacted': law.get('enacted'), 'published': law['published'], 'url': law['pdf'],
                            'temporary_until': None, 'restores': None, 'note': None}
        log.append(f'{law["key"]}: in force {law["in_force"]}; {sorted(r["changes"])}')
        prev_day = law['in_force']
    for c in cps:
        if c['id'] not in results:
            results[c['id']] = checkpoint(state, c['capture'])
    for line in log:
        print(line)
    expl = spec.get('explained', {})
    for c in cps:
        r = results[c['id']]
        ex = expl.get(c['id'], {})
        open_ = [x for x in r if '%s %s' % (x[0], x[1]) not in ex and x[0] not in ex]
        print('checkpoint %s (%s): %d differences, %d unexplained' % (c['id'], c['date'], len(r), len(open_)))
        if os.environ.get('PE_DIFF'):
            for k, w, d in open_:
                print('   ', k, w, d[:400])
    laws['dleg-635'] = spec['dleg635']
    part = {
        'laws': {k: laws[k] for k in sorted(laws)},
        'acts': [{
            'slug': SLUG, 'short': 'CP', 'title': 'Código Penal (Decreto Legislativo 635)',
            'url': spec['act_url'], 'first_law': None, 'earlier_laws': ['dleg-635'],
            'publisher': spec['publisher'], 'versions': versions,
        }],
        'sources': spec['sources'],
        'decisions': spec['decisions'] + derived_decisions(spec, results),
        'ai_use': spec['ai_use'],
    }
    if os.environ.get('PE_DRY'):
        print('dry run:', len(versions), 'versions', len(laws), 'laws')
        return
    tmp = PART.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, PART)
    print('wrote', PART, len(versions), 'versions', len(laws), 'laws')


if __name__ == '__main__':
    main()
