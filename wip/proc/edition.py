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


def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s)
    s = s.replace(' ', ' ').replace(' ', ' ').replace(' ', ' ').replace('\t', ' ')
    s = s.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
    return s


def _kind(span) -> str:
    f, size = span['font'], span['size']
    if f.startswith('Bahnschrift') or f.startswith('DINPro'):
        return 'furniture'
    if size < 5.3:
        return 'mark'
    if size < 6.65:
        return 'note'
    return 'body'


def lines(doc: fitz.Document, first: int, last: int) -> list[Line]:
    out: list[Line] = []
    for pn in range(first, last + 1):
        page = doc[pn]
        h = page.rect.height
        raw = []  # (kind, y, x, text, bold, size)
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    k = _kind(s)
                    if k == 'furniture':
                        continue
                    y = s['origin'][1]
                    if y > h - 38:      # page number band
                        continue
                    raw.append((k, y, s['origin'][0], s['text'], bool(s['flags'] & 16) or 'Bold' in s['font'], s['size']))
        # group into visual lines: body (with its marks) and notes separately
        groups: list[list] = []
        for item in sorted(raw, key=lambda r: (r[1], r[2])):
            k = 'note' if item[0] == 'note' else 'body'
            yy = item[1] + (2.0 if item[0] == 'mark' else 0.0)   # superscripts sit ~2pt high
            for g in reversed(groups[-4:]):
                if g[0] == k and abs(g[1] - yy) < 2.2:
                    g[2].append(item)
                    break
            else:
                groups.append([k, yy, [item]])
        for k, y, items in groups:
            items.sort(key=lambda r: r[2])
            text = ''
            spans = []
            for it in items:
                t = norm(it[3])
                if it[0] == 'mark':
                    if t.strip():
                        text += MARK + t.strip() + MARK
                    continue
                text += t
                if t.strip():
                    spans.append((t, it[4], it[2]))
            if not text.strip():
                continue
            vis = [it for it in items if it[0] != 'mark' and it[3].strip()]
            if not vis:   # a line of only marks: attach to the previous body line
                for prev in reversed(out):
                    if prev.kind == 'body' and prev.page == pn:
                        prev.text = prev.text.rstrip() + text.strip()
                        break
                continue
            out.append(Line(pn, y, vis[0][2], k, text, vis[0][4], vis[0][5], spans))
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
                                       [s for s in l.spans if s[0].strip() != m.group(1)]))
            continue
        if cur is None:
            continue
        notes[cur].append(l)
    return body, notes


def read(path: str, first: int, last: int):
    doc = fitz.open(path)
    ls = lines(doc, first, last)
    return split_notes(ls)
