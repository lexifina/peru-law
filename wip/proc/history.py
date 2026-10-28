"""Rebuild each provision's history from a MINJUS edition's footnotes.

Every amendment footnote names the law and its publication day and, for a change of wording,
quotes the text before it ("Texto anterior a la modificación:"). A quoted text carries its own
footnotes ((*), (**), ...) for the amendments before that one, so one edition gives the whole
chain back to 2004. Partial quotes keep the article heading, then "(…)" around the numeral,
literal or paragraph that changed.

rewind() walks one provision back from the edition's text, newest change first.
"""
from __future__ import annotations

import datetime as dt
import re

from edition import CALL, MARK, HEAD, DISP, LABEL as LABEL_RE, Note, label_of

MONTHS = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
          'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
DATE = r'(\d{1,2})\s+de\s+(%s)\s+(?:de|del)\s+(\d{4})' % '|'.join(MONTHS)
PUB = re.compile(r'publicad[oa]s?\s+el\s+(?:día\s+)?' + DATE, re.I)
LAWREF = re.compile(r'(Decreto\s+Legislativo|Ley|Decreto\s+de\s+Urgencia|Decreto\s+Supremo|Resolución\s+Legislativa)'
                    r'\s*N\s*[°ºo]?\s*\.?\s*(\d[\d\-]*(?:-[A-Z]+)?)', re.I)
WORDS = re.compile(r'^(?P<scope>.{0,60}?)\s*(?P<act>modificad[oa]s?|incorporad[oa]s?|derogad[oa]s?|sustituid[oa]s?|'
                   r'adicionad[oa]s?|agregad[oa]s?)\s+(?:por|mediante)\b', re.I)
COMMENCE = re.compile(r'vigencia\s+adelantada|adelanta(?:r)?\s+la\s+vigencia|entrada\s+en\s+vigencia|'
                      r'entra(?:rá|n|rán)?\s+en\s+vigencia|entró\s+en\s+vigencia\s+(?:en\s+todo|a\s+nivel|desde)',
                      re.I)
SEP = re.compile(r'^\(\s*(?:\.\.\.|…)\s*\)\s*\.?\s*$')


def iso(d, m, y) -> str:
    return dt.date(int(y), MONTHS[m.lower()], int(d)).isoformat()


def plus(day: str, **kw) -> str:
    d = dt.date.fromisoformat(day)
    if 'months' in kw:
        m = d.month - 1 + kw['months']
        return d.replace(year=d.year + m // 12, month=m % 12 + 1).isoformat()
    return (d + dt.timedelta(days=kw['days'])).isoformat()


def law_key(kind: str, num: str) -> tuple[str, str]:
    kind = re.sub(r'\s+', ' ', kind).lower()
    num = num.strip('-')
    if kind == 'decreto legislativo' and num == '10977':
        num = '1097'     # misprint in the 8th edition's note 204.1 ("Decreto Legislativo N° 10977"); 204.2 has 1097
    if kind == 'ley':
        return 'ley-%s' % num, 'Ley %s' % num
    if kind == 'decreto legislativo':
        return 'dleg-%s' % num, 'Decreto Legislativo %s' % num
    if kind == 'decreto de urgencia':
        return 'du-%s' % num.lower(), 'Decreto de Urgencia %s' % num
    if kind == 'decreto supremo':
        return 'ds-%s' % num.lower(), 'Decreto Supremo %s' % num
    return 'rl-%s' % num.lower(), 'Resolución Legislativa %s' % num


NUMWORDS = {'tres': 3, 'treinta': 30, 'sesenta': 60, 'noventa': 90, 'ciento veinte': 120, 'ciento ochenta': 180,
            'seis': 6, 'quince': 15, 'cuarenta y cinco': 45}


def vigencia(header: str, published: str | None):
    """(in-force day or None, how). Only what the note itself says; None means 'not stated'."""
    h = re.sub(r'\s+', ' ', header)
    m = re.search(r'(?:entró|entra|entraron) en vigencia (?:a nivel nacional |en todo el país )?el ' + DATE, h, re.I) or \
        re.search(r'vigente a partir del? ' + DATE, h, re.I)
    if m:
        return iso(*m.groups()), 'stated: ' + m.group(0)
    if not published:
        return None, None
    m = re.search(r'a los ([a-z ]+?)(?: \((\d+)\))? (días|meses)( (?:hábiles|calendario))?', h, re.I)
    if m and not m.group(2) and m.group(1).strip().lower() not in NUMWORDS:
        m = None
    if m and re.search(r'vigencia|vigente', h[max(0, m.start() - 160):m.end() + 40], re.I):
        n = int(m.group(2)) if m.group(2) else NUMWORDS[m.group(1).strip().lower()]
        if m.group(4) and 'hábiles' in m.group(4):
            return None, 'business days: ' + m.group(0)
        if m.group(3).lower() == 'meses':
            return plus(published, months=n), 'stated: ' + m.group(0)
        return plus(published, days=n), 'stated: ' + m.group(0)
    if re.search(r'vigente al día siguiente de la publicación de su Reglamento', h, re.I):
        return None, 'regulation: ' + h
    return None, None


class Event:
    def __init__(self, note: Note, kind: str, scope: str, act: str, law: tuple | None, published: str | None):
        self.note, self.kind, self.scope, self.act, self.law, self.published = note, kind, scope, act, law, published
        self.date: str | None = None

    def __repr__(self):
        return f'<{self.note.id} {self.kind} {self.scope}/{self.act} {self.law and self.law[0]} {self.date}>'


def classify(note: Note) -> Event:
    h = note.header
    m = PUB.search(h)
    published = iso(*m.groups()) if m else None
    lm = None
    w = WORDS.match(h)
    if w and not h.lower().startswith('de conformidad'):
        rest = h[w.end():]
        lm = LAWREF.search(rest)
        scope = w.group('scope').strip().lower()
        act = w.group('act').lower()[:6]
        law = law_key(*lm.groups()) if lm else None
        return Event(note, 'words', scope, act, law, published)
    if note.quote is not None and re.search(r'modific|sustitu|derog', h, re.I):
        # "De conformidad con el Artículo 2 del Decreto Legislativo N° 1575 … se dispuso la modificación del numeral 4"
        lm = LAWREF.search(h)
        sm = re.search(r'(?:modificación|sustitución|derogación)\s+del?\s+(?:la\s+)?(numeral|literal|inciso|párrafo|artículo)', h, re.I)
        act = 'deroga' if 'derog' in (note.quote_kind or '').lower() else 'modifi'
        return Event(note, 'words', sm.group(1).lower() if sm else 'artículo', act,
                     law_key(*lm.groups()) if lm else None, published)
    if re.search(r'fe de erratas', h, re.I):
        return Event(note, 'erratum', '', '', None, published)
    if COMMENCE.search(h) and not re.search(r'\bse modifica\b', h, re.I):
        lm = LAWREF.search(h)
        law = law_key(*lm.groups()) if lm else None
        return Event(note, 'commence', '', '', law, published)
    return Event(note, 'info', '', '', None, published)


def all_events(note: Note) -> list[Event]:
    out = [classify(note)]
    for s in note.subs.values():
        out += all_events(s)
    return out


# ---------------------------------------------------------------- rewinding one provision

def strip_calls(p: str) -> str:
    return CALL.sub('', p)


def calls_in(p: str) -> list[str]:
    return [c.strip(MARK) for c in CALL.findall(p)]


SCOPE_TYPES = {'numeral': ('num',), 'numerales': ('num',), 'inciso': ('num', 'inc', 'lit'), 'incisos': ('num', 'inc', 'lit'),
               'literal': ('lit',), 'literales': ('lit',)}


def _find(paras: list[str], call: str) -> int | None:
    for i, p in enumerate(paras):
        if MARK + call + MARK in p:
            return i
    return None


def _segments(quote: list[str]):
    """Heading (or None) and the runs of quoted paragraphs between the '(…)' separators. A call that sits on
    a separator belongs to the paragraph before it."""
    q = list(quote)
    head = None
    if q and (HEAD.match(strip_calls(q[0])) or DISP.match(strip_calls(q[0]))):
        head = q.pop(0)
    segs: list[list[str]] = []
    cur: list[str] = []
    partial = False
    split = []
    for p in q:
        # "… imparcialidad. (...)." : an ellipsis at the end of a quoted paragraph is a separator too
        m = re.search(r'\s*\(\s*(?:\.\.\.|…)\s*\)\s*\.?\s*((?:\x01[^\x01]*\x01)*)\s*$', p)
        if m and not SEP.match(strip_calls(p)) and strip_calls(p[:m.start()]).strip():
            split += [p[:m.start()], '(...)' + m.group(1)]
        else:
            split.append(p)
    if head is not None:
        m = re.search(r'\s*\(\s*(?:\.\.\.|…)\s*\)\s*\.?\s*((?:\x01[^\x01]*\x01)*)\s*$', head)
        if m:
            head = head[:m.start()] + m.group(1)
            partial = True
    for p in split:
        if SEP.match(strip_calls(p)):
            partial = True
            calls = ''.join(MARK + c + MARK for c in calls_in(p))
            if calls:
                if cur:
                    cur[-1] += calls
                elif segs:
                    segs[-1][-1] += calls
                elif head is not None:
                    head += calls
            if cur:
                segs.append(cur)
            cur = []
        else:
            cur.append(p)
    if cur:
        segs.append(cur)
    return head, segs, partial


class Problem(Exception):
    pass


def _block(paras: list[str], s: int, anchor: int | None) -> int:
    """End (exclusive) of the numbered block starting at paras[s]."""
    t = label_of(paras[s])[0]
    rank = {'num': 0, 'inc': 0, 'rom': 0, 'lit': 1}
    e = len(paras)
    for j in range(s + 1, len(paras)):
        lab = label_of(paras[j])
        if lab and rank.get(lab[0], 2) <= rank.get(t, 2):
            e = j
            break
    if anchor is not None and s <= anchor < e:
        e = anchor + 1
    return e


def undo(ev: Event, paras: list[str], log: list[str], unit: str):
    """The text before ev, as paragraphs with calls (None: the provision did not exist)."""
    a = _find(paras, ev.note.id)
    scope, act = ev.scope, ev.act
    first_word = scope.split()[0] if scope else ''
    whole = first_word in ('artículo', 'disposición') or scope.startswith('el artículo')
    if act.startswith('incorp') or act.startswith('adicio') or act.startswith('agrega'):
        if whole:
            if ev.note.quote:
                log.append(f'{unit} {ev.note.id}: "incorporado" with a quoted earlier text; using the quote')
                return list(ev.note.quote)
            return None
        if a is None:
            raise Problem(f'{unit} {ev.note.id}: incorporated {scope!r} but its call is not in the text')
        if a == 0:
            raise Problem(f'{unit} {ev.note.id}: incorporated {scope!r} but the call is on the heading')
        types = None
        for k, v in SCOPE_TYPES.items():
            if first_word == k:
                types = v
        s = a
        if types:
            while s > 0 and not (label_of(paras[s]) and label_of(paras[s])[0] in types):
                s -= 1
            if s == 0:
                log.append(f'{unit} {ev.note.id}: no {scope} label before the call; removing the paragraph only')
                s = a
        return paras[:s] + paras[a + 1:]
    # modified / substituted / repealed: needs the quoted earlier text
    if ev.note.quote is None:
        raise Problem(f'{unit} {ev.note.id}: {scope} {act} but the note quotes no earlier text')
    head, segs, partial = _segments(ev.note.quote)
    if not partial:
        out = ([head] if head is not None else []) + [p for s in segs for p in s]
        if head is None and paras and (HEAD.match(strip_calls(paras[0])) or DISP.match(strip_calls(paras[0]))):
            if whole:
                log.append(f'{unit} {ev.note.id}: full quote without a heading; keeping the current heading')
                return [paras[0]] + out
            # a quoted numeral without the article heading and without '(…)': treat as one segment
            segs = [out]
        else:
            return out
    out = list(paras)
    reps = []  # (start, end, new paragraphs)
    if head is not None and (first_word in ('epígrafe', 'encabezado', 'sumilla', 'artículo') or
                             re.sub(r'\W', '', strip_calls(head)).lower() != re.sub(r'\W', '', strip_calls(paras[0])).lower()):
        if strip_calls(head) != strip_calls(paras[0]) or first_word in ('epígrafe', 'sumilla') or                 (first_word == 'encabezado' and not segs):
            reps.append((0, 1, [head]))
    for seg in segs:
        lab = label_of(seg[0])
        labs = [label_of(p) for p in seg]
        deeper = [x for x in labs[1:] if x and x[0] == 'lit']
        if lab and lab[0] != 'lit' and deeper and deeper[0][1] != 'a':
            # a path: "1. Los Jueces se inhibirán …:" then "e) …" -- the numeral's lead-in is context, the
            # literal is what changed. Replace each quoted paragraph's own run, literals inside the numeral.
            cands = [i for i, p in enumerate(paras) if i and label_of(p) == lab]
            if not cands:
                raise Problem(f'{unit} {ev.note.id}: quoted {lab} not found in the current text')
            s0 = cands[-1] if a is None else max([i for i in cands if i <= a] or cands[:1])
            e0 = _block(paras, s0, None)
            runs = []
            for p, lb in zip(seg, labs):
                if lb or not runs:
                    runs.append([p])
                else:
                    runs[-1].append(p)
            for run in runs:
                lb = label_of(run[0])
                if re.fullmatch(r'\s*\(\s*(?:\.\.\.|…)\s*\)\s*\.?\s*', LABEL_RE.sub('', strip_calls(run[0]), count=1)):
                    continue   # "2. (...)": context only
                if lb == lab:
                    s, e = s0, s0 + 1
                    while e < e0 and not label_of(paras[e]):
                        e += 1
                else:
                    hits = [i for i in range(s0 + 1, e0) if label_of(paras[i]) == lb]
                    if not hits:
                        raise Problem(f'{unit} {ev.note.id}: quoted {lb} not found inside {lab}')
                    s = hits[0]
                    e = s + 1
                    while e < e0 and not label_of(paras[e]):
                        e += 1
                reps.append((s, e, run))
            continue
        if lab and re.fullmatch(r'\s*(?:\(\s*(?:\.\.\.|…)\s*\)\s*\.?)?\s*', LABEL_RE.sub('', strip_calls(seg[0]), count=1)):
            seg = seg[1:]          # "2. (...)" or a bare "2." then "b) …": the numeral is context
            if not seg:
                continue
            lab = label_of(seg[0])
        if lab:
            cands = [i for i, p in enumerate(paras) if i and label_of(p) == lab]
            if not cands and lab[0] == 'num':
                cands = [i for i, p in enumerate(paras) if i and label_of(p) and label_of(p)[1] == lab[1]]
            if not cands:
                if first_word in ('numeral', 'inciso', 'literal', 'numerales') and act.startswith('derog'):
                    pass
                raise Problem(f'{unit} {ev.note.id}: quoted {lab} not found in the current text')
            before = [i for i in cands if a is None or i <= a]
            s = before[-1] if before else cands[0]
            e = _block(paras, s, a)
            other_lits = any(label_of(sg[0]) and label_of(sg[0])[0] == 'lit' for sg in segs if sg is not seg)                 or first_word == 'encabezado'
            if other_lits and lab[0] != 'lit' and not any(x and x[0] == 'lit' for x in labs) and                     any(label_of(paras[i]) and label_of(paras[i])[0] == 'lit' for i in range(s + 1, e)):
                # the quote gives the numeral's lead-in only; its literals are quoted (or not) on their own
                e = s + 1
                while e < len(paras) and not label_of(paras[e]) and e < _block(paras, s, None):
                    e += 1
                e = min(e, s + len(seg)) if len(seg) == 1 else e
            reps.append((s, e, seg))
        else:
            if a is None:
                raise Problem(f'{unit} {ev.note.id}: unlabelled quoted paragraph and no call in the text')
            s = a
            if scope.startswith('primer párrafo'):
                s = 1
            if a == 0:
                raise Problem(f'{unit} {ev.note.id}: unlabelled quoted paragraph but the call is on the heading')
            reps.append((s, a + 1, seg))
    reps.sort()
    for (s1, e1, _), (s2, e2, _) in zip(reps, reps[1:]):
        if s2 < e1:
            raise Problem(f'{unit} {ev.note.id}: overlapping replacements {reps}')
    for s, e, new in reversed(reps):
        out[s:e] = new
    return out


def rewind(paras: list[str], notes: dict[str, Note], indate, log: list[str], unit: str):
    """[(day, laws, paragraphs)] ascending: the provision's text from each day on. The first entry has day None
    (the oldest text the notes reach) unless the provision was inserted, in which case its first day is the
    inserting law's. Also returns the no-words events (commencement) found on the way."""
    pending: list[Event] = []
    others: list[Event] = []

    def add(ns):
        for n in ns:
            ev = classify(n)
            if ev.kind == 'words':
                ev.date = indate(ev)
                pending.append(ev)
            else:
                others.append(ev)
                add(n.subs.values())

    add(notes.values())
    states = []
    cur = paras
    order = {id(e): i for i, e in enumerate(pending)}
    while pending:
        pending.sort(key=lambda e: (e.date or '', [int(x) for x in e.note.id.split('.')]))
        ev = pending.pop()
        if cur is None:
            raise Problem(f'{unit} {ev.note.id}: change {ev} to a provision that did not exist yet')
        prev = undo(ev, cur, log, unit)
        states.append((ev.date, ev.law[0] if ev.law else None, cur, ev))
        for s in ev.note.subs.values():
            add([s])
        cur = prev
    states.reverse()
    return cur, states, others
