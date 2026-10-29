"""The Código Penal as printed in the Ministry of Justice's twelfth official edition (May 2016, current to 31 May
2016), read from its text layer. Only the body is read: the footnotes (amendment notes, "Texto anterior", "De
conformidad con ...") and the footnote calls are left out by font size.

Layout of the edition: body Calibri 9 pt, sumillas and article headings ClarendonBT-Bold 9 pt at the left margin,
structure headings ClarendonBT-Bold 9-10 pt centred, footnote calls Calibri 5.2-6 pt superscripts, footnotes
Calibri 7 pt (numbers Calibri-Bold 8), running heads Calibri 6 pt and page numbers Calibri 11 pt.

    units(path) -> {key: {'label', 'kind', 'text'}}

Only the cache is read. No network.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'more'))
from edition import clean_par, label_of, roman  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)

URL = ('https://web.archive.org/web/20170517041248id_/http://spij.minjus.gob.pe:80/content/publicaciones_oficiales/'
       'img/CODIGOPENAL.pdf')
FIRST, LAST = 46, 253          # Título Preliminar .. Disposiciones finales y transitorias (0-based pages)

HEAD = re.compile(r'^Art[íi]culo\s+([IVXL]+|\d+)\s*[°º˚]?\s*(?:-\s*([A-ZÑ])\b)?\s*[°º˚]?\s*\.?\s*-?')
ORD = ['PRIMERA', 'SEGUNDA', 'TERCERA', 'CUARTA', 'QUINTA']
DFT = re.compile(r'^(%s)\s*\.-' % '|'.join(ORD))
STRUCT = re.compile(r'^(LIBRO|SECCI[ÓO]N|T[ÍI]TULO|CAP[ÍI]TULO|DISPOSICIONES)\b')


def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s)
    for a in ('\xa0', ' ', ' ', '\t'):
        s = s.replace(a, ' ')
    return s.replace('˚', '°').replace('ﬁ', 'fi').replace('ﬂ', 'fl')


def body_lines(doc):
    """[(page, y, x, x1, text, face)] where face is 'h' (ClarendonBT-Bold) or 'b' (body)."""
    out = []
    for pn in range(FIRST, LAST + 1):
        rows = []
        for b in doc[pn].get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    if s['size'] < 8.5 or s['size'] > 10.5:
                        continue
                    if not s['text'].strip() and not rows:
                        continue
                    rows.append((round(s['origin'][1], 1), s['origin'][0], s['bbox'][2], norm(s['text']),
                                 'h' if s['font'].startswith('ClarendonBT') or 'Bold' in s['font'] else 'b',
                                 s['size']))
        rows.sort()
        lines: list[list] = []
        for r in rows:
            if lines and abs(lines[-1][0][0] - r[0]) < 2.0:
                lines[-1].append(r)
            else:
                lines.append([r])
        for ln in lines:
            ln.sort(key=lambda r: r[1])
            vis = [r for r in ln if r[3].strip()]
            if not vis:
                continue
            text = ''.join(r[3] for r in ln)
            # a heading run, then body text on the same line: keep the boundary
            out.append({'page': pn, 'y': ln[0][0], 'x': vis[0][1], 'x1': max(r[2] for r in vis), 'text': text,
                        'face': vis[0][4], 'size': vis[0][5],
                        'head_part': ''.join(r[3] for r in ln if r[4] == 'h').strip(),
                        'body_part': ''.join(r[3] for r in ln if r[4] != 'h').strip()})
    return out


def _join(a: str, b: str) -> str:
    a = a.rstrip()
    if a.endswith('\xad'):
        return a[:-1] + b.lstrip()
    if a.endswith('-') and not a.endswith(' -'):
        return a + b.lstrip()
    return a + ' ' + b.lstrip()


def units(path) -> dict:
    doc = fitz.open(str(path))
    ls = body_lines(doc)
    right = max(l['x1'] for l in ls)
    out: dict[str, dict] = {}
    cur = None            # current unit dict with 'paras'
    sumilla: list[str] = []
    in_dft = False
    expect_title = False
    prev = None
    for l in ls:
        t = l['text'].strip()
        if l['face'] == 'h':
            hp = l['head_part']
            m = HEAD.match(hp)
            d = DFT.match(hp) if in_dft else None
            if m or d:
                if m:
                    base, suf = m.group(1), m.group(2)
                    if re.fullmatch(r'[IVXL]+', base):
                        key, label = 'tp-%02d' % roman(base), 'Título Preliminar, art. %s' % base
                    else:
                        key = 'art-%03d%s' % (int(base), ('-' + suf.lower()) if suf else '')
                        label = 'Art. %s' % (base + ('-' + suf if suf else ''))
                    kind = 'art'
                else:
                    n = ORD.index(d.group(1)) + 1
                    key, label, kind = 'dft-%02d' % n, 'Disposición final y transitoria %s' % d.group(1).lower(), \
                        'provision'
                if key in out:
                    raise SystemExit(f'duplicate unit {key} on page {l["page"] + 1}')
                cur = {'label': label, 'kind': kind, 'paras': list(sumilla)}
                sumilla = []
                out[key] = cur
                cur['paras'].append(t)
                cur['break'] = not l['body_part']      # "Artículo 36°.- Inhabilitación" on a line of its own
                prev = l
                continue
            if cur is not None and cur.get('break') and prev is not None and prev['face'] == 'h' \
                    and l['page'] == prev['page'] and l['y'] - prev['y'] < 14 and l['x'] < 84:
                cur['paras'][-1] = _join(cur['paras'][-1], t)       # a heading set on two or three lines
                cur['break'] = not l['body_part']
                prev = l
                continue
            if STRUCT.match(t) or (l['x'] > 84 and not in_dft):
                if t.startswith('DISPOSICIONES FINALES'):
                    in_dft = True
                # "CAPÍTULO I" is followed by the chapter's title, which a long title sets at the margin
                expect_title = bool(STRUCT.match(t))
                cur = None
                sumilla = []
                prev = l
                continue
            if expect_title and not sumilla:
                expect_title = False
                prev = l
                continue
            if prev is not None and prev['face'] == 'h' and sumilla and l['y'] - prev['y'] < 14 \
                    and l['page'] == prev['page']:
                sumilla[-1] = _join(sumilla[-1], t)
            else:
                sumilla.append(t)
            cur = None
            prev = l
            continue
        if cur is None:
            prev = l
            continue
        new = True
        if prev is not None and prev is not l:
            if l['page'] == prev['page']:
                new = l['y'] - prev['y'] > 14.5
            else:
                new = prev['x1'] < right - 25
            if label_of(t) is not None and not (l['page'] == prev['page'] and l['y'] - prev['y'] < 2):
                new = True
        if cur.pop('break', False):
            new = True
        if new:
            cur['paras'].append(t)
        else:
            cur['paras'][-1] = _join(cur['paras'][-1], t)
        prev = l
    res = {}
    for k, u in out.items():
        # a footnote call dropped between a word and its punctuation leaves a space: "artículo 36° ."
        paras = [re.sub(r'(\S) +([.,;:])(?=\s|$)', r'\1\2', clean_par(p)) for p in u['paras']]
        paras = [p for p in paras if p]
        text = ''.join(p + '\n' for p in paras)
        if re.search(r'(?:^|\n)Art[íi]culo[^\n]*?DEROGADOS?\.?\n$', text):
            continue        # a repealed article, printed as a placeholder: no text in force
        res[k] = {'label': u['label'], 'kind': u['kind'], 'text': text}
    return res


if __name__ == '__main__':
    sys.path.insert(0, str(HERE.parent))
    import fetch
    u = units(fetch.path_for(URL))
    print(len(u))
    for k in sys.argv[1:]:
        print(k, u.get(k, {}).get('text'))
