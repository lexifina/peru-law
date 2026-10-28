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
import forward  # noqa: E402
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


CHECKPOINTS = {
    # earlier MINJUS official editions: url, pages, layout profile, structure-heading size, "actualizada hasta"
    'ed5-2018': ('https://cdn.www.gob.pe/uploads/document/file/1535454/CODIGO%20PROCESAL%20PENAL%20D.L.%20957.pdf.pdf?v=1610046523',
                 (20, 356), 'ed5', 10.0, '2018-11-23'),
    'ed6-2020': ('https://cdn.www.gob.pe/uploads/document/file/1850571/C%C3%B3digo%20Procesal%20Penal%20Final.pdf?v=1619548796',
                 (19, 408), 'ed6', 11.5, '2020-11-27'),
    'ed7-2022': ('https://cdn.www.gob.pe/uploads/document/file/3710113/C%C3%B3digo%20Procesal%20Penal.pdf?v=1664488493',
                 (30, 381), 'ed7', 9.9, '2022-08-01'),
}


def words(paras) -> str:
    t = ' '.join(strip_calls(p) for p in paras)
    t = re.sub(r'(Art[íi]culo\s+[IVXL\d]+)\s*[°º˚]', r'\1', t)
    t = re.sub(r'\(\s*sic\s*\)', ' ', t)                       # an edition's own "(sic)"
    t = re.sub(r'(?:^|\s)(?:\d{1,2}|[a-z])\s*[.)]\s*DEROGAD[OA]\b\.?', ' ', t)   # placeholders for repealed items
    return ' '.join(re.findall(r'\w+', t.lower()))


def word_diff(a: str, b: str, n: int = 6) -> str:
    import difflib
    a, b = a.split(), b.split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag != 'equal':
            out.append(f'[{" ".join(a[i1:i2])[:150]} => {" ".join(b[j1:j2])[:150]}]')
    return f'{len(out)} edits: ' + ' '.join(out[:n])


def checkpoint(url, pages, prof, big, date, lines_of):
    import statistics
    body, _ = edition.read(str(fetch.cached(url)), *pages, prof)
    sp = [b.y - a.y for a, b in zip(body, body[1:]) if a.page == b.page and 0 < b.y - a.y < 30]
    units, _ = edition.units(body, gap=statistics.median(sp) * 1.45, big=big)
    theirs = {u['key']: u['paras'] for u in units}
    res = {'same': [], 'diff': [], 'missing_here': [], 'missing_there': []}
    for key, tl in lines_of.items():
        cur = None
        for day, pub, ls, paras in tl:
            if (pub or '0000') <= date:
                cur = paras
        if cur is None:
            if key in theirs:
                res['missing_here'].append(key)
            continue
        if key not in theirs:
            res['missing_there'].append(key)
            continue
        a, b = words(cur), words(theirs[key])
        (res['same'] if a == b else res['diff']).append(key if a == b else (key, a, b))
    return res


# Start days the notes do not give by themselves, with where they come from.
OVERRIDE: dict[str, tuple[str, str]] = {
    # "vigente al día siguiente de la publicación de su Reglamento": D.S. 007-2019-JUS, El Peruano 1 Feb 2019
    'dleg-1373': ('2019-02-02', 'the day after its Reglamento (D.S. 007-2019-JUS), published 2019-02-01: '
                                'https://busquedas.elperuano.pe/dispositivo/NL/1737282-3'),
}


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
    # per unit: [(in-force day, publication day, laws, paragraphs or None)] ascending; day None = as enacted
    pubday = {k: v['published'] for k, v in laws.items()}
    lines_of = {}
    for key, (orig, states) in timelines.items():
        tl = []
        if orig is not None:
            tl.append((None, PUBLISHED, ['dleg-957'], orig))
        for day, law, paras, ev in states:
            tl.append((day, pubday.get(law), [law] if law else [], paras))
        lines_of[key] = tl
    checks = {}
    for name, (url, pages, prof, big, date) in CHECKPOINTS.items():
        if fetch.cached(url) is None:
            continue
        checks[name] = checkpoint(url, pages, prof, big, date, lines_of)
    corpus = assemble(path, units, laws, lines_of, commence, trees, checks, log)
    if report:
        for name, res in checks.items():
            print(f'CHECKPOINT {name} ({CHECKPOINTS[name][4]}): {len(res["same"])} same, {len(res["diff"])} differ, '
                  f'missing here {res["missing_here"]}, missing there {res["missing_there"]}')
            for k, a, b in res['diff']:
                print(f'   {k}: {word_diff(a, b)}')
        print('PROBLEMS', len(problems))
        for p in problems:
            print('  ', p)
        print('LOG', len(log))
        for l in log:
            print('  ', l)
    return locals()


MONTHS_ABBR = {'Ene': 1, 'Feb': 2, 'Mar': 3, 'Abr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Ago': 8, 'Set': 9, 'Sep': 9,
               'Oct': 10, 'Nov': 11, 'Dic': 12}


def districts() -> list[tuple[str, str]]:
    """(day, district) from MINJUS's implementation map: each name is set with its start day just below it."""
    import fitz
    d = fitz.open(str(fetch.cached(MAPA)))
    names, dates = [], []
    for b in d[0].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text'].strip()
                m = re.search(r'(\d\d) (\w{3})\. (\d{4})', t)
                y, x = s['origin'][1], s['origin'][0]
                if m:
                    day = '%s-%02d-%s' % (m.group(3), MONTHS_ABBR[m.group(2)], m.group(1))
                    head = t[:m.start()].strip()
                    if head:              # "LIMA SUR 31 May. 2021" on one line
                        names.append((y, x, head, day))
                    else:
                        dates.append((y, x, day))
                elif s['font'].startswith('DINPro-Bold') and t and t == t.upper():
                    names.append((y, x, t, None))
    out = []
    used = set()
    for y, x, name, day in names:
        if day is None:
            cands = [(abs(dy - y - 7) + abs(dx - x) / 10, i) for i, (dy, dx, dd) in enumerate(dates)
                     if i not in used and 0 < dy - y < 12]
            if not cands:
                continue
            i = min(cands)[1]
            used.add(i)
            day = dates[i][2]
        out.append((day, name.title().replace(' De ', ' de ').replace(' Del ', ' del ')))
    return sorted(out)


def unit_obj(u, paras):
    return {'label': u['label'], 'kind': u['kind'], 'text': text_of(paras)}


def assemble(path, units, laws, lines_of, commence, trees, checks, log):
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    by_key = {u['key']: u for u in units}
    order = [u['key'] for u in units]
    used_laws = {'dleg-957'}
    events: dict[str, dict] = {}      # day -> {'changes': {}, 'credits': {}, 'notes': []}

    def ev(day):
        return events.setdefault(day, {'changes': {}, 'credits': {}, 'notes': []})

    first_units = {}
    for key in order:
        tl = lines_of.get(key)
        if not tl:
            continue
        last = {}
        for day, pub, ls, paras in tl:
            if day is None:
                first_units[key] = unit_obj(by_key[key], paras)
                continue
            last[day] = (ls, paras)
            e = ev(day)
            e['credits'].setdefault(key, [])
            for l in ls:
                if l not in e['credits'][key]:
                    e['credits'][key].append(l)
                used_laws.add(l)
        for day, (ls, paras) in last.items():
            ev(day)['changes'][key] = unit_obj(by_key[key], paras) if paras is not None else None

    # commencement: notes that bring provisions into force ahead of the district calendar
    groups: dict[tuple, list[str]] = {}
    for key, e in commence:
        h = e.note.header
        m = re.search(r'suspende hasta el ' + history.DATE, h, re.I)
        stated, _ = vigencia(h, e.published)
        if key == 'promulgacion':
            if not (e.law and e.law[0] == 'ley-30077'):
                continue         # the edition's general notes on the title; each article carries its own
            key = 'disp-final-01'
        if m:
            day = history.iso(*m.groups())
        elif stated:
            day = stated
        elif e.law:
            day = laws[e.law[0]]['in_force']
        else:
            log.append(f'commencement note {e.note.id} names no law; left out')
            continue
        law = e.law[0] if e.law else None
        groups.setdefault((day, law, h), []).append(key)
    for (day, law, h), keys in sorted(groups.items()):
        e = ev(day)
        for k in keys:
            e['credits'].setdefault(k, [])
            if law and law not in e['credits'][k]:
                e['credits'][k].append(law)
        used_laws.add(law)
        labels = ', '.join(by_key[k]['label'] for k in keys)
        e['notes'].append(f'{labels}: the MINJUS edition notes: "{h}"')

    # the Code's own staged start: Primera Disposición Final, numeral 4, and the district calendar
    num4 = ['art-468', 'art-469', 'art-470', 'art-471'] + [k for k in order if k.startswith('art-') and
                                                         508 <= int(k[4:7]) <= 566] + ['disp-modif-derog-02']
    e = ev('2006-02-01')
    for k in num4:
        e['credits'].setdefault(k, []).append('dleg-957')
    e['notes'].append('Primera Disposición Final, numeral 4 (as amended by Leyes 28460 and 28671): from 1 February 2006 '
                      'arts. 468-471, Libro Séptimo (arts. 508-566) and the Disposiciones Modificatorias apply '
                      'throughout the country, except numerals 5, 6 and 7 of the Segunda Disposición Modificatoria '
                      '(from 1 July 2006). Elsewhere the Code applies by judicial district under the Calendario Oficial.')
    for day, name in districts():
        e = ev(day)
        e['credits'].setdefault('disp-final-01', [])
        if 'ds-013-2005-jus' not in e['credits']['disp-final-01']:
            e['credits']['disp-final-01'].append('ds-013-2005-jus')
        e['notes'].append(f'The Code starts to apply in the judicial district of {name} (MINJUS implementation map, 2021).')
    used_laws.add('ds-013-2005-jus')

    days = sorted(d for d in events if d)
    if any(d <= D0 for d in days):
        raise SystemExit(f'an event before the first version: {[d for d in days if d <= D0]}')
    versions = [{'from': D0, 'source_url': ED8, 'sha256': sha, 'units': dict(sorted(first_units.items())),
                 'credits': {}, 'note': FIRST_NOTE}]
    for d in days:
        e = events[d]
        v = {'from': d, 'source_url': ED8, 'sha256': sha,
             'changes': dict(sorted(e['changes'].items())),
             'credits': {k: sorted(ls) for k, ls in sorted(e['credits'].items()) if ls}}
        notes = list(dict.fromkeys(e['notes']))
        if notes:
            v['note'] = ' '.join(notes)
        versions.append(v)

    # The eighth-edition point: the replayed state must equal the edition's own text, word for word.
    state = {}
    for v in versions:
        for k, u in (v.get('units') or v.get('changes') or {}).items():
            if u is None:
                state.pop(k, None)
            else:
                state[k] = u
    ed8 = {u['key']: text_of(u['paras']) for u in units}
    bad = sorted(k for k in set(ed8) | set(state) if ed8.get(k) != (state.get(k) or {}).get('text'))
    if bad:
        raise SystemExit(f'the state after the last eighth-edition version differs from the edition: {bad[:20]}')
    log.append(f'eighth-edition point: {len(ed8)} provisions equal the edition\'s text exactly')

    # After the edition: the laws' own texts (proc/forward.py)
    paras_now = {k: [l for l in u['text'].split('\n') if l] for k, u in state.items()}
    labels = {k: u['label'] for k, u in state.items()}
    extra_laws = {}
    for n, pub, day, sha_l, url, title, changed in forward.apply(paras_now, labels):
        key = f'ley-{n}'
        credits = {}
        changes = {}
        for k, paras in sorted(changed.items()):
            if k in state:
                lab, kind = state[k]['label'], state[k]['kind']
            else:
                m = re.fullmatch(r'art-(\d+)(?:-([a-z]))?', k)
                lab, kind = 'Art. %d%s' % (int(m.group(1)), '-' + m.group(2).upper() if m.group(2) else ''), 'art'
            u = {'label': lab, 'kind': kind, 'text': ''.join(p + '\n' for p in paras)}
            if versions[-1]['from'] == day:
                prev = versions[-1]
            else:
                prev = None
            changes[k] = u
            credits[k] = [key]
            state[k] = u
        if prev is not None:
            prev['changes'].update(changes)
            for k, ls in credits.items():
                prev['credits'][k] = sorted(set(prev['credits'].get(k, [])) | set(ls))
            prev['source_url'] = url if prev['source_url'] == url else prev['source_url']
        else:
            versions.append({'from': day, 'source_url': url, 'sha256': sha_l, 'changes': changes,
                             'credits': credits})
        extra_laws[key] = {'label': f'Ley {n}', 'title': title, 'kind': 'law', 'enacted': None, 'published': pub,
                           'url': url, 'temporary_until': None, 'restores': None, 'note': None}
        used_laws.add(key)

    law_objs = {}
    for key in sorted(k for k in used_laws if k):
        if key in extra_laws:
            law_objs[key] = extra_laws[key]
            continue
        if key in EXTRA_LAWS:
            law_objs[key] = EXTRA_LAWS[key]
            continue
        L = laws[key]
        kind = 'law' if key.startswith('ley-') else 'decree'
        law_objs[key] = {'label': L['label'], 'title': None, 'kind': kind, 'enacted': None,
                         'published': L['published'], 'url': None, 'temporary_until': None, 'restores': None,
                         'note': None}
    act = {'slug': 'codigo-procesal-penal', 'short': 'NCPP',
           'title': 'Código Procesal Penal (Decreto Legislativo 957)',
           'url': ED8_PAGE, 'first_law': 'dleg-957', 'earlier_laws': [], 'versions': versions}
    return {'laws': law_objs, 'acts': [act], 'sources': SOURCES, 'decisions': decisions(laws, checks, log),
            'ai_use': ['none: no model wrote or chose any legal text; parsing is rule-based (proc/edition.py, proc/history.py).']}


FIRST_NOTE = ('Decreto Legislativo 957 as published in El Peruano on 29 July 2004, rebuilt from the "Texto anterior" '
              'footnotes of the Ministry of Justice\'s eighth official edition (current to 17 November 2024). The Code '
              'applied by stages under its Primera Disposición Final; the commencement commits that follow record '
              'each step.')

EXTRA_LAWS = {
    'dleg-957': {'label': 'Decreto Legislativo 957', 'title': 'Nuevo Código Procesal Penal', 'kind': 'decree',
                 'enacted': '2004-07-22', 'published': '2004-07-29',
                 'url': 'https://www.leyes.congreso.gob.pe/Documentos/DecretosLegislativos/00957.pdf',
                 'temporary_until': None, 'restores': None, 'note': None},
    'ds-013-2005-jus': {'label': 'Decreto Supremo 013-2005-JUS',
                        'title': 'Aprueban Plan de Implementación y Calendario Oficial de la Aplicación Progresiva del '
                                 'Código Procesal Penal', 'kind': 'decree', 'enacted': None, 'published': '2005-10-08',
                        'url': None, 'temporary_until': None, 'restores': None,
                        'note': 'The Calendario Oficial approved by this decree, as later amended by further supreme '
                                'decrees, brings the Code into force one judicial district at a time. The district is '
                                'named below. The source (the Ministry of Justice\'s implementation map) gives the day '
                                'but not the amending decree that set it, so every step is credited to the calendar.'},
}

SOURCES = [
    {'name': 'Ministerio de Justicia y Derechos Humanos: Código Procesal Penal, Octava Edición Oficial (diciembre 2024, '
             'actualizada al 17 de noviembre de 2024)', 'url': ED8, 'retrieved': '2026-10-28', 'requests': 1,
     'licence': 'Official text (Peruvian legal norms are not subject to copyright, D.Leg. 822 art. 9)',
     'notes': 'PDF with a text layer, 396 pages. Footnotes quote the wording before each amendment ("Texto anterior a '
              'la modificación"), nested back to 2004. Body NotoSans 8 pt, footnotes NewsGothic 6 pt.'},
    {'name': 'MINJUS: Código Procesal Penal, Séptima Edición Oficial (actualizada al 1 de agosto de 2022)',
     'url': 'https://cdn.www.gob.pe/uploads/document/file/3710113/C%C3%B3digo%20Procesal%20Penal.pdf?v=1664488493',
     'retrieved': '2026-10-28', 'requests': 1, 'licence': 'as above', 'notes': 'checkpoint only'},
    {'name': 'MINJUS: Código Procesal Penal, Sexta Edición Oficial (actualizada al 27 de noviembre de 2020)',
     'url': 'https://cdn.www.gob.pe/uploads/document/file/1850571/C%C3%B3digo%20Procesal%20Penal%20Final.pdf?v=1619548796',
     'retrieved': '2026-10-28', 'requests': 1, 'licence': 'as above', 'notes': 'checkpoint only'},
    {'name': 'MINJUS: Código Procesal Penal, edición oficial actualizada al 23 de noviembre de 2018',
     'url': 'https://cdn.www.gob.pe/uploads/document/file/1535454/CODIGO%20PROCESAL%20PENAL%20D.L.%20957.pdf.pdf?v=1610046523',
     'retrieved': '2026-10-28', 'requests': 1, 'licence': 'as above', 'notes': 'checkpoint only'},
    {'name': 'MINJUS: Mapa de implementación del Código Procesal Penal (2021)', 'url': MAPA, 'retrieved': '2026-10-28',
     'requests': 1, 'licence': 'as above', 'notes': 'start day of the Code in each of the 34 judicial districts'},
    {'name': 'El Peruano: Decreto Supremo 007-2019-JUS (Reglamento del Decreto Legislativo 1373), publicado el 1 de febrero de 2019',
     'url': 'https://busquedas.elperuano.pe/dispositivo/NL/1737282-3', 'retrieved': '2026-10-28', 'requests': 1,
     'licence': 'as above', 'notes': 'dates the start of Decreto Legislativo 1373 (the day after its regulation)'},
]


AFTER_DECISIONS = [
    'The history ends with the eighth edition (current to 17 November 2024). Amendments published after that day '
    'are not in it yet: no official consolidated text after that day was found (no ninth MINJUS edition; El '
    'Peruano\'s Normas Legales Actualizadas PDFs are served corrupted; SPIJ is unreachable), so this part is not '
    'marked verified (no 60-proc.PUBLISH).',
    'Known later amendments, not yet replayed: in the Congreso law index (leyes.congreso.gob.pe, searched by number '
    'from Ley 32140; the index ends at Ley 32537 of 26 December 2025) the titles of Leyes 32181 and 32182 '
    '(11 December 2024), 32255 (10 March 2025) and 32374 (7 June 2025) name the Code. Laws of 2026 and '
    'decretos legislativos are not in that index.',
]


def decisions(laws, checks, log):
    out = [
        'Código Procesal Penal part (proc/parse_proc.py, corpus.d/60-proc.json) is built from the Ministry of Justice\'s '
        'eighth official edition (text layer, no OCR). The footnotes there quote the wording before each amendment, '
        'and quoted texts carry their own footnotes, so one edition gives the chain back to 2004; proc/history.py '
        'replays it backwards, newest change first.',
        'The El Peruano 2004 publication and the Congreso copy of Decreto Legislativo 957 are image scans and are not '
        'used (no OCR). The first version is the text the footnotes reach back to, credited to Decreto Legislativo 957.',
        'In-force days: the day after publication (Constitución art. 109) unless the edition\'s note gives the law\'s own '
        'start ("a los noventa (90) días", "entró en vigencia el 1 de julio de 2014"); "a los N días de su publicación" '
        'is counted as publication day + N.',
        'Decreto Legislativo 1373 took effect the day after its Reglamento was published; D.S. 007-2019-JUS was '
        'published on 1 February 2019 (El Peruano), so 2 February 2019.',
        'Footnotes that bring provisions into force ahead of the district calendar ("Vigencia adelantada", '
        '"se adelanta la vigencia") are commits that change no words, credited to the law the note names and dated '
        'by the note or by that law\'s start; the note\'s own words are quoted in the commit. Ley 28366 suspended '
        'arts. 205-210 until 1 January 2005, which is the day used for them.',
        'District-by-district entry into force follows the Ministry of Justice\'s implementation map (2021): one '
        'no-words commit per start day, on the Primera Disposición Final, credited to the Calendario Oficial '
        '(D.S. 013-2005-JUS and its amendments).',
        'Footnotes that only interpret, list related rules or report a Fe de Erratas are not commits; the edition\'s '
        'text is used as printed (it says it is a faithful copy of El Peruano).',
        'Structure headings (libros, secciones, títulos, capítulos) are not tracked: the footnotes do not give their '
        'history.',
        'Where a numbered item was repealed the edition keeps a placeholder ("5. DEROGADO"); so does this history.',
        'Decreto Legislativo 1097 appears once as "10977" in the edition (note 204.1); read as 1097, as in note 204.2.',
    ] + AFTER_DECISIONS
    for name, res in checks.items():
        out.append(f'Checkpoint {name}: of the provisions in both, {len(res["same"])} match the rebuilt text at that '
                   f'edition\'s date word for word (case and the editions\' own "(sic)" ignored) and {len(res["diff"])} '
                   f'differ: ' + '; '.join(f'{k} ({word_diff(a, b, 2)})' for k, a, b in res['diff'])[:3000])
    return out


def write(corpus, out: Path):
    data = json.dumps(corpus, ensure_ascii=False, indent=1, sort_keys=False) + '\n'
    tmp = out.with_suffix('.json.tmp')
    tmp.write_text(data, encoding='utf-8', newline='\n')
    os.replace(tmp, out)
    return len(data)


if __name__ == '__main__':
    report = '--report' in sys.argv
    r = build(report=report)
    out = Path(sys.argv[sys.argv.index('--out') + 1]) if '--out' in sys.argv else OUT
    if r['problems']:
        print('not written: problems remain', file=sys.stderr)
        sys.exit(1)
    n = write(r['corpus'], out)
    vs = r['corpus']['acts'][0]['versions']
    print(f'wrote {out} ({n} bytes): {len(vs)} versions, {len(r["corpus"]["laws"])} laws')
