"""Read a MINJUS official edition of the Código Procesal Penal (PDF with a text layer).

The editions set the body in NotoSans 8 pt (headings bold, structure headings bold 9 pt), the
footnote calls as 4.7 pt superscripts, and the footnotes in NewsGothicMT 6 pt. Font size alone
separates the three, so no layout guessing is needed.

    lines(pdf)  -> visual lines: page, y, x, kind (body|note), text, bold flags
    read(pdf)   -> {'body': [Line...], 'notes': {n: [Line...]}}

Only the cache is read. No network.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import fitz  # PyMuPDF

MARK = '\x01'  # footnote call in body text: MARK + number + MARK


@dataclass
class Line:
    page: int
    y: float
    x: float
    kind: str              # 'body' or 'note'
    text: str
    bold: bool             # first visible span is bold
    size: float
    spans: list = field(default_factory=list)   # (text, bold, x)
    x1: float = 0.0        # right edge of the last visible span


def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s)
    s = s.replace(' ', ' ').replace(' ', ' ').replace(' ', ' ').replace('\t', ' ')
    s = s.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return s


# Per edition: body text size floor, furniture fonts, top/bottom bands (running heads, page numbers).
PROFILES = {
    'ed8': {'body_min': 6.8, 'furniture': ('Bahnschrift', 'DINPro'), 'top': 0, 'bottom': 38},
    'ed7': {'body_min': 8.9, 'furniture': (), 'top': 48, 'bottom': 30},
    'ed6': {'body_min': 9.5, 'furniture': (), 'top': 48, 'bottom': 30},
    'ed5': {'body_min': 8.0, 'furniture': (), 'top': 48, 'bottom': 30},
}


def lines(doc: fitz.Document, first: int, last: int, profile: str = 'ed8') -> list[Line]:
    """Visual lines. Body spans are at least the profile's body size; a smaller span on a body line is a
    footnote call; smaller spans on lines of their own are footnote text."""
    P = PROFILES[profile]
    out: list[Line] = []
    for pn in range(first, last + 1):
        page = doc[pn]
        h = page.rect.height
        big, small = [], []   # (y, x, text, bold, size, x1)
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    if s['font'].startswith(P['furniture']) if P['furniture'] else False:
                        continue
                    y = s['origin'][1]
                    if y > h - P['bottom'] or y < P['top']:
                        continue
                    it = (y, s['origin'][0], s['text'], bool(s['flags'] & 16) or 'Bold' in s['font'], s['size'],
                          s['bbox'][2])
                    (big if s['size'] >= P['body_min'] else small).append(it)
        groups: list[list] = []   # [y, items]
        for it in sorted(big):
            for g in reversed(groups[-4:]):
                if abs(g[0] - it[0]) < 2.2:
                    g[1].append(it)
                    break
            else:
                groups.append([it[0], [it]])
        marks: dict[int, list] = {}
        notes = []
        for it in small:
            home = None
            for gi, g in enumerate(groups):
                lo = min(x[1] for x in g[1]) - 15
                hi = max(x[5] for x in g[1]) + 40
                if g[0] - 7 <= it[0] <= g[0] + 1.5 and lo <= it[1] <= hi:
                    if re.fullmatch(r'\s*(\d{1,3}\s*)+', it[2]) or not it[2].strip():
                        home = gi
                        break
            if home is None:
                notes.append(it)
            else:
                marks.setdefault(home, []).append(it)
        ngroups: list[list] = []
        for it in sorted(notes):
            for g in reversed(ngroups[-4:]):
                if abs(g[0] - it[0]) < 2.2:
                    g[1].append(it)
                    break
            else:
                ngroups.append([it[0], [it]])
        rows = [('body', g[0], g[1], marks.get(gi, [])) for gi, g in enumerate(groups)] +                [('note', g[0], g[1], []) for g in ngroups]
        rows.sort(key=lambda r: (r[0] == 'note', r[1]))
        for k, y, items, mk in rows:
            items = sorted(items + [(m[0], m[1], m[2], m[3], m[4], m[5], 'mark') for m in mk], key=lambda r: r[1])
            text = ''
            spans = []
            for it in items:
                t = norm(it[2])
                if len(it) > 6:
                    text += ''.join(MARK + tok + MARK for tok in t.split())
                    continue
                text += t
                if t.strip():
                    spans.append((t, it[3], it[1]))
            vis = [it for it in items if len(it) == 6 and it[2].strip()]
            if not vis:
                continue
            out.append(Line(pn, y, vis[0][1], k, text, vis[0][3], vis[0][4], spans, max(it[5] for it in vis)))
    return out


NOTE_START = re.compile(r'^(\d{1,4})\s*(?:\s|$)')


def split_notes(ls: list[Line]) -> tuple[list[Line], dict[int, list[Line]]]:
    """Body lines in order, and footnotes by number (continuations across pages folded in)."""
    body = [l for l in ls if l.kind == 'body']
    notes: dict[int, list[Line]] = {}
    cur = None
    expect = 1
    for l in ls:
        if l.kind != 'note':
            continue
        m = NOTE_START.match(l.text.strip())
        if m and l.x < 70 and int(m.group(1)) in (expect, expect + 1) and not l.bold:
            cur = int(m.group(1))
            expect = cur + 1
            rest = l.text.strip()[len(m.group(1)):].lstrip()
            notes[cur] = []
            if rest:
                notes[cur].append(Line(l.page, l.y, l.x + 20, 'note', rest, False, l.size,
                                       [s for s in l.spans if s[0].strip() != m.group(1)], l.x1))
            continue
        if cur is None:
            continue
        notes[cur].append(l)
    return body, notes


def read(path: str, first: int, last: int, profile: str = 'ed8'):
    doc = fitz.open(path)
    ls = lines(doc, first, last, profile)
    return split_notes(ls)


# ---------------------------------------------------------------- paragraphs

LABEL = re.compile(r'^(?:(\d{1,3})\s*\.(?=\s|$)|(\d{1,3})\s*\)|([a-zñ])\s*\)|([a-zñ])\s*\.(?=\s)|([IVX]+)\s*\.(?=\s))')
CALL = re.compile(r'\x01[^\x01]*\x01')
ELLIPSIS = re.compile(r'^\s*\(\s*(?:\.\.\.|…)\s*\)\s*\.?\s*$')


def label_of(p: str):
    """('num', '2') for '2. …', ('inc', '2') for '2) …', ('lit', 'a') for 'a) …'; None otherwise."""
    m = LABEL.match(CALL.sub('', p).strip())
    if not m:
        return None
    if m.group(1):
        return ('num', m.group(1))
    if m.group(2):
        return ('inc', m.group(2))
    if m.group(3) or m.group(4):
        return ('lit', m.group(3) or m.group(4))
    return ('rom', m.group(5))


def clean_par(p: str) -> str:
    p = re.sub(r'[ ]+', ' ', p.replace('\n', ' ')).strip()
    p = re.sub(r'\s+(\x01)', r'\1', p)            # no space before a call
    p = re.sub(r'(\x01[^\x01]*\x01)\s+(?=\x01)', r'\1', p)
    p = p.replace('“', '"').replace('”', '"').replace('„', '"').replace('‘', "'").replace('’', "'")
    p = p.replace('–', '-').replace('—', '-').replace('…', '...')
    p = re.sub(r'^(\d{1,3}\.|\d{1,3}\)|[a-zñ]\))(?=["A-ZÁÉÍÓÚÑa-záéíóúñ])', r'\1 ', p)   # a dropped tab after a label
    return p


def paragraphs(ls: list[Line], gap: float) -> list[str]:
    """Join visual lines into paragraphs. A paragraph ends where a line does not end in a space
    (the editions keep the space at every soft wrap), at a vertical gap, or before a numbered item."""
    out: list[str] = []
    prev = None
    right = max((l.x1 for l in ls), default=0)
    for l in ls:
        t = l.text
        new = True
        if prev is not None and out:
            same_flow = (l.page == prev.page and 0 < l.y - prev.y < gap) or (l.page == prev.page + 1)
            soft = prev.text.endswith(' ') or prev.x1 > right - 30
            new = not (same_flow and soft) or label_of(t) is not None or ELLIPSIS.match(CALL.sub('', t)) is not None \
                or ELLIPSIS.match(CALL.sub('', prev.text)) is not None
        if new:
            out.append(t.strip())
        else:
            out[-1] = out[-1].rstrip() + ' ' + t.strip()
        prev = l
    return [c for c in (clean_par(p) for p in out) if c]


# ---------------------------------------------------------------- units of the body

HEAD = re.compile(r'^Art[íi]culo\s+([IVXL]+|\d+(?:\s*-\s*[A-Z])?)\s*°?\s*(?:\.?\s*-|\.(?=\s+[A-ZÁÉÍÓÚ]))')
ORD = ['Primera', 'Segunda', 'Tercera', 'Cuarta', 'Quinta', 'Sexta', 'Sétima', 'Octava', 'Novena', 'Décima']
DISP = re.compile(r'^(%s|Séptima)\s*\.-' % '|'.join(ORD))
STRUCT = re.compile(r'^(LIBRO|SECCI[ÓO]N|T[ÍI]TULO|CAP[ÍI]TULO|SUBCAP[ÍI]TULO|DISPOSICIONES)\b')
ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50}


def roman(s: str) -> int:
    n = 0
    for a, b in zip(s, s[1:] + ' '):
        v = ROMAN[a]
        n += -v if b != ' ' and ROMAN.get(b, 0) > v else v
    return n


def upper_only(t: str) -> bool:
    t = CALL.sub('', t)
    return any(c.isalpha() for c in t) and not any(c.islower() for c in t)


def art_key(head: str) -> tuple[str, str]:
    m = HEAD.match(CALL.sub('', head).strip())
    num = re.sub(r'\s', '', m.group(1))
    if re.fullmatch(r'[IVXL]+', num):
        return 'tp-%02d' % roman(num), 'Título Preliminar, art. %s' % num
    base, _, suf = num.partition('-')
    return 'art-%03d%s' % (int(base), ('-' + suf.lower()) if suf else ''), 'Art. %s' % num


DISP_NAMES = {'df': ('disp-final', 'Disposición final'),
              'dmd': ('disp-modif-derog', 'Disposición modificatoria y derogatoria')}


def disp_key(head: str, group: str) -> tuple[str, str]:
    w = DISP.match(CALL.sub('', head).strip()).group(1)
    w = 'Sétima' if w == 'Séptima' else w
    k, lab = DISP_NAMES[group]
    return '%s-%02d' % (k, ORD.index(w) + 1), '%s %s' % (lab, w.lower())


def units(body: list[Line], gap: float = 14.5, big: float = 8.9):
    """Split the body into units: an ordered list of dicts {key, label, kind, lines, paras}, plus the
    structure headings as (text with calls, index of the next unit)."""
    out = []
    struct: list[tuple[str, int]] = []
    cur = None
    group = 'promulgacion'
    disp_group = None
    for l in body:
        t = l.text.strip()
        tc = CALL.sub('', t).strip()
        if l.bold and tc.startswith('TÍTULO PRELIMINAR') and group == 'promulgacion':
            group = 'code'
        if group == 'promulgacion':
            if cur is None:
                cur = {'key': 'promulgacion', 'label': 'Decreto Legislativo 957 (promulgación)', 'kind': 'preamble',
                       'lines': [], 'head': None}
                out.append(cur)
            cur['lines'].append(l)
            continue
        if l.bold and not HEAD.match(tc) and not DISP.match(tc) and (
                l.size >= big or (upper_only(t) and (l.x > 60 or STRUCT.match(tc)))):
            if tc.startswith('DISPOSICIONES'):
                if 'FINALES' in tc:
                    disp_group = 'df'
                elif 'MODIFICATORIAS' in tc:
                    disp_group = 'dmd'
            struct.append((t, len(out)))
            cur = None
            continue
        if l.bold and HEAD.match(tc) and disp_group is None:
            key, label = art_key(tc)
            cur = {'key': key, 'label': label, 'kind': 'art', 'lines': [l], 'head': l}
            out.append(cur)
            continue
        if l.bold and DISP.match(tc) and disp_group:
            key, label = disp_key(tc, disp_group)
            cur = {'key': key, 'label': label, 'kind': 'provision', 'lines': [l], 'head': l}
            out.append(cur)
            continue
        if cur is None:
            continue
        cur['lines'].append(l)
    for u in out:
        u['paras'] = unit_paras(u, gap)
    return out, struct


def unit_paras(u, gap):
    ls = u['lines']
    if u['head'] is None:
        return paragraphs(ls, gap)
    head = [ls[0]]
    j = 1
    while j < len(ls) and ls[j].bold and ls[j].x < 70 and label_of(ls[j].text) is None:
        head.append(ls[j])
        j += 1
    h = clean_par(' '.join(x.text.strip() for x in head))
    return [h] + paragraphs(ls[j:], gap)


# ---------------------------------------------------------------- footnote trees

@dataclass
class Note:
    id: str
    header: str
    quote: list | None = None      # paragraphs of "Texto anterior a la modificación/derogación", calls as MARK
    quote_kind: str | None = None
    subs: dict = field(default_factory=dict)
    lines: list = field(default_factory=list)


STAR = re.compile(r'^\s*\((\*+)\)')
TEXTO_ANTERIOR = re.compile(r'^\s*Texto\s+(?:anterior|original)', re.I)


def _is_sub_start(l: Line) -> bool:
    return bool(l.spans) and l.spans[0][1] and STAR.match(l.spans[0][0] or '') is not None


def _calls(l: Line, nid: str) -> str:
    t = l.text
    if not any(b and '(*' in s for s, b, _ in l.spans):
        return t
    return re.sub(r'\((\*+)\)', lambda m: MARK + '%s.%d' % (nid, len(m.group(1))) + MARK, t)


def note_tree(ls: list[Line], nid: str, gap: float = 10.5) -> Note:
    """One footnote as a tree. A line opening with a bold (*), (**), ... starts a nested note; it belongs to
    the innermost open note whose quoted text calls that many stars (editors both restart and continue the
    star count at deeper levels, and indent inconsistently, so the calls decide, not the indentation)."""
    root = Note(nid, '', lines=ls)
    head: dict[str, list[str]] = {nid: []}
    quote: dict[str, list[Line]] = {}
    expect: dict[str, set] = {nid: set()}
    stack = [root]
    for i, l in enumerate(ls):
        cur = stack[-1]
        if i and _is_sub_start(l):
            k = len(STAR.match(l.spans[0][0]).group(1))
            j = len(stack) - 1
            while j >= 0 and not (k in expect[stack[j].id] and k not in stack[j].subs):
                j -= 1
            if j < 0:   # no quote calls it: the innermost note that has a quote
                j = len(stack) - 1
                while j > 0 and stack[j].id not in quote:
                    j -= 1
            parent = stack[j]
            del stack[j + 1:]
            child = Note('%s.%d' % (parent.id, k), '')
            parent.subs[k] = child
            stack.append(child)
            head[child.id] = [STAR.sub('', l.text, count=1).strip()]
            expect[child.id] = set()
            continue
        if l.bold and TEXTO_ANTERIOR.match(l.text) and cur.id not in quote:
            quote[cur.id] = []
            cur.quote_kind = l.text.strip()
            continue
        if cur.id in quote:
            t = _calls(l, cur.id)
            for m in re.finditer(MARK + r'%s\.(\d+)' % re.escape(cur.id) + MARK, t):
                expect[cur.id].add(int(m.group(1)))
            quote[cur.id].append(Line(l.page, l.y, l.x, l.kind, t, l.bold, l.size, l.spans, l.x1))
        else:
            head[cur.id].append(l.text.strip())

    def fill(n: Note):
        n.header = clean_par(' '.join(head.get(n.id, [])))
        if n.id in quote:
            n.quote = paragraphs(quote[n.id], gap)
        for c in n.subs.values():
            fill(c)
    fill(root)
    return root
