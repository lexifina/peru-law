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
                # StagSans is El Peruano's furniture: running heads, sector headings and the issue's summary
                spans = [s for s in l['spans'] if not s['font'].startswith('StagSans')]
                if not spans:
                    continue
                t = ''.join(s['text'] for s in spans)
                if not t.strip():
                    continue
                x0, y0 = min(s['bbox'][0] for s in spans), min(s['bbox'][1] for s in spans)
                x1, y1 = max(s['bbox'][2] for s in spans), max(s['bbox'][3] for s in spans)
                if y1 < top or y0 > bottom:
                    continue
                sz = max(s['size'] for s in spans)
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
    # Paragraphs. Two settings occur: a first-line indent (first line 13 pt in, the rest at the margin) and, in some
    # laws, hanging items ("1. …" at the margin, its continuation lines indented). A new paragraph starts at an item
    # label, at a line indented past the previous one (unless the previous line opened an item: a hanging
    # continuation), at a vertical gap, or after a line that stopped short at a full stop.
    out: list[str] = []
    prev = None
    prev_label = False
    hang = None
    for l in ls[start:end]:
        pn, col, y, x0, x1, t, left, right = l
        s = t.strip()
        is_label = bool(LABEL_START.match(s)) or bool(ELL_LINE.match(s)) or \
            (prev is not None and bool(ELL_LINE.match(prev[5].strip())))     # "[…]" stands alone
        new = True
        if prev is not None and out:
            same = (pn, col) == (prev[0], prev[1])
            if is_label:
                new = True
            elif same:
                if x0 > prev[3] + 6:
                    new = not prev_label and not (hang is not None and abs(x0 - hang) < 3)
                    if not new:
                        hang = x0
                elif hang is not None and abs(x0 - hang) < 3:
                    new = False
                elif hang is not None and x0 < hang - 6:
                    new = True           # back out of a hanging item
                else:
                    new = y - prev[2] > 14
                if not new and x0 > left + 6 and prev[4] < prev[7] - 25 and not (hang and abs(x0 - hang) < 3):
                    new = True           # an indented line after a line that stopped short
            else:
                new = x0 > left + 6 and not (hang is not None and abs(x0 - (hang - prev[6] + left)) < 3)
            if not new and prev[4] < prev[7] - 25 and re.search(r'[.:;”"]$', prev[5].rstrip()) \
                    and re.match(r'["“]?[A-ZÁÉÍÓÚÑ\[(]', s):
                new = True       # the previous line stopped short after a full stop: it ended a paragraph
        if new:
            out.append(s)
            prev_label = is_label
            if not is_label:
                hang = None
        else:
            out[-1] = _join(out[-1], t)
            prev_label = False
        prev = l
    return [' '.join(p.split()) for p in out if p.strip()]


ELL_LINE = re.compile(r'^[“"]?[\[(]\s*(?:…|\.\s*\.\s*\.)\s*[\])]\s*[.,;]?\s*[”"]?\s*[.,;]?$')
LABEL_START = re.compile(r'^[“"]?(?:\d{1,3}(?:\.\d{1,3})*\.\s|\d{1,3}\)\s|[a-zñ]\)\s|[a-zñ]\.\s+(?=[A-ZÁÉÍÓÚÑ]))')


if __name__ == '__main__':
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import fetch
    p = fetch.cached(sys.argv[1])
    for x in paragraphs(p, sys.argv[2], sys.argv[3]):
        print('¶', x)
