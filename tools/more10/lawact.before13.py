"""One act built from its own law as published in El Peruano (no Editora Perú consolidation exists): the first version is
the law's text read from El Peruano's PDF of that law (penal/lawtext.py cuts its paragraphs); later amending norms are
replayed with build_nla's compositions; "staged" paragraphs that the law itself makes apply from a later day enter on
that day (listed in decisions). Output in build_nla's single-act format (.tmp/p7/<name>.json), joined by more5/merge.py.

    python -X utf8 more9/lawact.py more2/<name>.json         (env DRY=1: print the units, no write)

Spec: part, slug, short, title, title_short, law {key,label,title,kind,enacted,published,in_force,vigencia,op,pdf,heading},
cut {split: [[paragraph index, text the second piece starts with], ...], start: regex of the first unit's paragraph},
staged [{key, date, drop: [line prefixes absent before date], note}], laws [build_nla law records], sources, decisions,
ai_use, publisher.
"""
from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'more2'))
sys.path.insert(0, str(ROOT / 'penal'))
import build_nla  # noqa: E402
import nlaunits  # noqa: E402

ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
STRUCT = re.compile(r'^(?:LIBRO|TÍTULO|CAPÍTULO|SUBCAPÍTULO|SECCIÓN)\s+[IVXL]+$')
ART = re.compile(r'^Artículo (?P<n>\d+|único)(?:-(?P<s>[A-Z]))?\.\s')
SECTIONS = [(re.compile(r'^DISPOSICI[ÓO]N(?:ES)? COMPLEMENTARIAS? FINAL(?:ES)?$'), 'dcf', 'complementaria final'),
            (re.compile(r'^DISPOSICI[ÓO]N(?:ES)? COMPLEMENTARIAS? TRANSITORIAS?$'), 'dct', 'complementaria transitoria'),
            (re.compile(r'^DISPOSICI[ÓO]N(?:ES)? COMPLEMENTARIAS? MODIFICATORIAS?$'), 'dcm', 'complementaria modificatoria'),
            (re.compile(r'^DISPOSICI[ÓO]N(?:ES)? COMPLEMENTARIAS? DEROGATORIAS?$'), 'dcd', 'complementaria derogatoria')]
DISP = re.compile(r'^(?P<o>(?:[A-ZÁÉÍÓÚ]+)(?: [A-ZÁÉÍÓÚ]+)?)\.\s')
ANNEX = re.compile(r'^ANEXO (?P<n>[IVXL]+|\d+)\b')


def roman(s: str) -> int:
    n = 0
    for a, b in zip(s, s[1:] + ' '):
        v = ROMAN[a]
        n += -v if b != ' ' and ROMAN[b] > v else v
    return n


def is_caps(p: str) -> bool:
    letters = [c for c in p if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters)


def cut(paras: list[str], splits) -> list[str]:
    """Paragraphs El Peruano's layout runs together (a heading and its first paragraph): split where the spec says."""
    out = list(paras)
    for i, ats in sorted(splits, key=lambda s: -s[0]):
        p, pieces = out[i], []
        for at in ([ats] if isinstance(ats, str) else ats):
            k = p.index(at)
            pieces.append(p[:k].strip())
            p = p[k:]
        out[i:i + 1] = pieces + [p.strip()]
    return out


def segment(paras: list[str], start: str) -> tuple[dict, list[str]]:
    units: dict = {}
    skipped: list[str] = []
    i0 = next(i for i, p in enumerate(paras) if re.search(start, p))
    cur, section, in_struct, done = None, None, False, False
    for p in paras[i0:]:
        m = ANNEX.match(p)
        if m:
            n = int(m.group('n')) if m.group('n').isdigit() else roman(m.group('n'))
            cur, done = 'anexo-%02d' % n, False
            units[cur] = {'label': 'Anexo %s' % m.group('n'), 'kind': 'provision', 'lines': [p]}
            continue
        if done:
            skipped.append(p)
            continue
        if re.match(r'^Comun[íi]quese', p):
            done, cur = True, None
            skipped.append(p)
            continue
        if cur and cur.startswith('anexo'):
            units[cur]['lines'].append(p)
            continue
        sec = next(((k, name) for rx, k, name in SECTIONS if rx.match(p)), None)
        if sec:
            section, cur, in_struct = sec, None, False
            skipped.append(p)
            continue
        if section is None:
            m = ART.match(p)
            if m:
                in_struct = False
                if m.group('n') == 'único':
                    cur = 'tp-01'
                    units[cur] = {'label': 'Título Preliminar, artículo único', 'kind': 'art', 'lines': [p]}
                else:
                    n, s = int(m.group('n')), m.group('s')
                    cur = 'art-%03d%s' % (n, '-' + s.lower() if s else '')
                    units[cur] = {'label': 'Art. %d%s' % (n, '-' + s if s else ''), 'kind': 'art', 'lines': [p]}
                continue
            if STRUCT.match(p) or (in_struct and is_caps(p)):
                in_struct, cur = True, None
                skipped.append(p)
                continue
        else:
            m = DISP.match(p)
            o = nlaunits.ordinal(m.group('o')) if m else None
            if m and (o or m.group('o') == 'ÚNICA'):
                n = 1 if m.group('o') == 'ÚNICA' else o
                cur = '%s-%02d' % (section[0], n)
                if cur in units:
                    raise SystemExit(f'duplicate {cur}')
                units[cur] = {'label': 'Disposición %s %s' % (section[1], m.group('o').lower()), 'kind': 'provision',
                              'lines': [p]}
                continue
        if cur is None:
            raise SystemExit(f'paragraph outside a unit: {p[:100]}')
        units[cur]['lines'].append(p)
    return units, skipped


def main(spec_path: str):
    spec = json.loads(Path(spec_path).read_text(encoding='utf-8'))
    law = spec['law']
    paras, sha = build_nla.law_paras(law)
    paras = cut(paras, spec.get('cut', {}).get('split', []))
    for j in spec.get('cut', {}).get('join', []):     # a paragraph the layout breaks before a numeral at a line start
        i = paras.index(j)
        paras[i:i + 2] = [paras[i] + ' ' + paras[i + 1]]
    units, skipped = segment(paras, spec['cut']['start'])
    if os.environ.get('DRY'):
        for k, v in units.items():
            print('==', k, '|', v['label'])
            print('\n'.join(v['lines']) if os.environ.get('FULL') else ' | '.join(x[:70] for x in v['lines'][:3]),
                  '| n', len(v['lines']))
        print('skipped:', skipped)
        return
    staged = spec.get('staged', [])
    first = {k: dict(v, lines=list(v['lines'])) for k, v in units.items()}
    for st in staged:
        u = first[st['key']]
        keep = [x for x in u['lines'] if not any(x.startswith(d) for d in st['drop'])]
        if len(keep) == len(u['lines']):
            raise SystemExit(f'staged {st["key"]}: nothing dropped')
        u['lines'] = keep
    k0 = law['key']
    versions = [{'from': law['in_force'], 'source_url': law['pdf'], 'sha256': sha,
                 'units': {k: build_nla.as_unit(first[k]) for k in sorted(first)}, 'credits': {},
                 'note': spec['first_note']}]
    for st in staged:
        u = units[st['key']]
        versions.append({'from': st['date'], 'source_url': law['pdf'], 'sha256': sha,
                         'changes': {st['key']: build_nla.as_unit(u)}, 'credits': {st['key']: [k0]}, 'note': st['note']})
    laws = {k0: {k: law.get(k) for k in ('label', 'title', 'kind', 'enacted', 'published')} |
            {'url': law['pdf'], 'temporary_until': None, 'restores': None, 'note': None}}
    cur = {k: dict(v, lines=list(v['lines'])) for k, v in units.items()}
    for lw in sorted(spec.get('laws', []), key=lambda l: (l['in_force'], l['key'])):
        lp, lsha = build_nla.law_paras(lw)
        ch = build_nla.apply_law(lw, cur, lp)
        if not ch:
            raise SystemExit(f'{lw["key"]}: no change')
        versions.append({'from': lw['in_force'], 'source_url': lw['pdf'], 'sha256': lsha,
                         'changes': {k: (build_nla.as_unit(cur[k]) if k in cur else None) for k in sorted(ch)},
                         'credits': {k: [lw['key']] for k in sorted(ch)},
                         'note': f'Wording of {lw["label"]} from its El Peruano text ({lw["pdf"]}).'})
        laws[lw['key']] = {k: lw.get(k) for k in ('label', 'title', 'kind', 'enacted', 'published')} | \
            {'url': lw['pdf'], 'temporary_until': None, 'restores': None, 'note': None}
    versions.sort(key=lambda v: v['from'])
    for a, b in zip(versions, versions[1:]):
        if a['from'] == b['from']:
            b['same_day'] = True
    act = {'slug': spec['slug'], 'short': spec['short'], 'title': spec['title'], 'url': law['pdf'], 'first_law': k0,
           'earlier_laws': [], 'versions': versions}
    if spec.get('publisher'):
        act['publisher'] = spec['publisher']
    part = {'laws': {k: laws[k] for k in sorted(laws)}, 'acts': [act], 'sources': spec['sources'],
            'decisions': spec['decisions'], 'ai_use': spec['ai_use']}
    out = (ROOT / 'corpus.d' / spec['part']).resolve()
    tmp = out.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, out)
    print('wrote', out, len(versions), 'versions', len(laws), 'laws')


if __name__ == '__main__':
    main(sys.argv[1])
