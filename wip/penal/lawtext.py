"""Paragraphs of one norm from its El Peruano PDF extract (busquedas.elperuano.pe /api/archivo/file/<token>/*/<op>.pdf).

El Peruano sets Normas Legales in two columns per page; a paragraph's first line is indented about 13 pt; justified
lines are sometimes cut into one text line per word (they are regrouped by baseline). The extract holds whole pages,
so it can start or end inside a neighbouring norm: the norm runs from its heading ("LEY Nº …" / "DECRETO LEGISLATIVO
Nº …") to the line holding its own operation number (e.g. "1471010-2"), which El Peruano prints under every norm.

    paragraphs(path, op, heading_regex) -> [str]
"""
from __future__ import annotations

import re
import unicodedata

import fitz

fitz.TOOLS.mupdf_display_errors(False)
OPLINE = re.compile(r'^\d{6,7}-\d{1,2}$')


def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s)
    for a in ('\xa0', ' ', ' ', '\t'):
        s = s.replace(a, ' ')
    return s.replace('ﬁ', 'fi').replace('ﬂ', 'fl')


def lines(doc):
    """[(page, col, y, x0, x1, text, col_left, col_right)] in reading order."""
    out = []
    for pn in range(doc.page_count):
        page = doc[pn]
        mid = page.rect.width / 2
        top, bottom = 80, page.rect.height - 20
        items = []
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = ''.join(s['text'] for s in l['spans'])
                if not t.strip():
                    continue
                x0, y0, x1, y1 = l['bbox']
                if y1 < top or y0 > bottom:
                    continue
                sz = max(s['size'] for s in l['spans'])
                if sz < 6.5:
                    continue
                # a line straddling the gutter (a full-width title) belongs to column 0
                col = 0 if x0 < mid - 8 else 1
                items.append((col, round(y1, 1), x0, x1, norm(t)))
        items.sort()
        rows: list[list] = []
        for it in items:
            if rows and rows[-1][0][0] == it[0] and abs(rows[-1][0][1] - it[1]) < 2.5:
                rows[-1].append(it)
            else:
                rows.append([it])
        for c in (0, 1):
            cr = [r for r in rows if r[0][0] == c]
            if not cr:
                continue
            xs = sorted(min(i[2] for i in r) for r in cr)
            left = xs[len(xs) // 10] if len(xs) > 10 else xs[0]
            right = max(max(i[3] for i in r) for r in cr)
            for r in cr:
                r.sort(key=lambda i: i[2])
                out.append((pn, c, r[0][1], r[0][2], max(i[3] for i in r), ' '.join(i[4].strip() for i in r),
                            left, right))
    return out


VOCAB: set = set()        # word forms known from the 2016 edition (set by the caller), to read line-end hyphens


def _join(a: str, b: str) -> str:
    a = a.rstrip()
    b = b.lstrip()
    if a.endswith('\xad'):
        return a[:-1] + b
    if a.endswith('-') and len(a) > 1 and a[-2].isalpha() and b[:1].islower():
        left = re.search(r'(\w+)-$', a).group(1)
        right = re.match(r'\w+', b).group(0) if re.match(r'\w+', b) else ''
        if (left + '-' + right).lower() in VOCAB and (left + right).lower() not in VOCAB:
            return a + b           # a hyphenated compound that fell at the line end ("días-multa")
        return a[:-1] + b          # a word broken at the line end
    if a.endswith('-'):
        return a + b
    return a + ' ' + b


def paragraphs(path, op: str, heading: str) -> list[str]:
    doc = fitz.open(str(path))
    ls = lines(doc)
    end = next((i for i, l in enumerate(ls) if l[5].strip() == op), None)
    if end is None:
        raise SystemExit(f'{op}: operation number not found in {path}')
    # the norm starts after the previous norm's operation number (or at the top of the extract); heading is a
    # regex the norm's own title must match, as a check that the right text was cut
    start = 0
    for i in range(end - 1, -1, -1):
        if OPLINE.match(ls[i][5].strip()):
            start = i + 1
            break
    head = ' '.join(l[5] for l in ls[start:start + 6])
    if not re.search(heading, head, re.I):
        # the first norm of an issue: the extract starts with the issue's summary; the norm starts at its own
        # heading line(s) ("LEY Nº 30556", or "decreto legislativo" / "nº 1323")
        hre = re.compile(r'\s*' + heading + r'\s*', re.I)
        for i in range(start, end):
            if hre.fullmatch(ls[i][5]) or (i + 1 < end and hre.fullmatch(ls[i][5] + ' ' + ls[i + 1][5])):
                start = i
                break
        else:
            raise SystemExit(f'{op}: heading {heading!r} not in {head[:200]!r}')
    out: list[str] = []
    prev = None
    for l in ls[start:end]:
        pn, col, y, x0, x1, t, left, right = l
        new = True
        if prev is not None and out:
            indent = x0 > left + 6
            if (pn, col) == (prev[0], prev[1]):
                gap = y - prev[2]
                new = indent or gap > 14
            else:
                new = indent
            if not new and prev[4] < prev[7] - 25 and not prev[5].rstrip().endswith(('-', ',')):
                new = True       # the previous line stopped short: it ended a paragraph
        if new:
            out.append(t.strip())
        else:
            out[-1] = _join(out[-1], t)
        prev = l
    return [' '.join(p.split()) for p in out if p.strip()]


if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import fetch
    p = fetch.cached(sys.argv[1])
    for x in paragraphs(p, sys.argv[2], sys.argv[3]):
        print('¶', x)
