"""Editora Perú's Normas Legales Actualizadas: Código Penal (diariooficial.elperuano.pe/Normas/obtenerDocumento?
idNorma=2), read from Internet Archive captures for word-level checkpoints. Never a source of wording.

Layout: two columns; body ArialMT 9 pt, sumillas and article headings Arial-BoldMT 9 pt, Editora Perú's notes
Arial-BoldItalicMT 8 pt ("(*) Artículo modificado por ..."), running heads in StagSans. Captures from September
2026 on replace every non-ASCII byte with U+FFFD and are not used.

    segments(path) -> [(key, text after the heading up to the next heading, [notes])]
The text of a segment ends with whatever precedes the next heading: structure headings and the next sumilla.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'more'))
from edition import roman  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)

BASE = 'https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=2'
HEAD = re.compile(r'(?:(?<=\n)|^)[“"]?\s*Art[íi]culo\s+([IVXL]+|\d+)\s*[°º]?\s*(?:-?\s*([A-ZÑ])\b)?\s*[°º]?\s*'
                  r'(?:\.\s*-|\.(?=\s+[A-ZÁÉÍÓÚÑ(“"])|-(?=\s+[A-ZÁÉÍÓÚÑ]))')
DISP = re.compile(r'\b(PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA)\s*\.\s*-', re.I)
ORD = ['PRIMERA', 'SEGUNDA', 'TERCERA', 'CUARTA', 'QUINTA']


def url(ts: str) -> str:
    return f'https://web.archive.org/web/{ts}id_/{BASE}'


def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s)
    for a in ('\xa0', ' ', ' ', '\t'):
        s = s.replace(a, ' ')
    return s


def stream(doc):
    """[(text, is_note)] runs in reading order (column by column)."""
    out = []
    for pn in range(doc.page_count):
        page = doc[pn]
        mid = page.rect.width / 2
        rows = []
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    f = s['font']
                    if f.startswith('StagSans') or s['size'] < 7.5:
                        continue
                    if s['size'] < 7.6 and 'Bold' in f:        # "Inicio" link
                        continue
                    if not s['text'].strip():
                        continue
                    rows.append((0 if s['origin'][0] < mid - 5 else 1, round(s['origin'][1], 1), s['origin'][0],
                                 norm(s['text']), 'Italic' in f and 'Bold' in f))
        rows.sort()
        grp: list[list] = []
        for r in rows:
            if grp and grp[-1][0][0] == r[0] and abs(grp[-1][0][1] - r[1]) < 2.0:
                grp[-1].append(r)
            else:
                grp.append([r])
        for g in grp:
            g.sort(key=lambda r: r[2])
            for r in g:
                out.append((r[3], r[4]))
            out.append(('\n', False))
    return out


def segments(path):
    doc = fitz.open(str(path))
    runs = stream(doc)
    body = ''
    notes_at = []          # (offset in body, note text)
    note = ''
    for t, is_note in runs:
        if is_note:
            note += t
            continue
        if note and t != '\n':
            notes_at.append((len(body), ' '.join(note.split())))
            note = ''
        body += t
    if note:
        notes_at.append((len(body), ' '.join(note.split())))
    body = re.sub(r'\xad\n', '', body)
    flat = body
    start = flat.find('Artículo I.-')
    m = re.search(r'DISPOSICIONES FINALES\s+Y\s+TRANSITORIAS', flat[start:])
    dft = start + m.start() if m else -1
    heads = []
    for m in HEAD.finditer(flat, start):
        if dft != -1 and m.start() > dft:
            break
        base, suf = m.group(1), m.group(2)
        key = 'tp-%02d' % roman(base) if re.fullmatch(r'[IVXL]+', base) else \
            'art-%03d%s' % (int(base), ('-' + ('nn' if suf == 'Ñ' else suf.lower())) if suf else '')
        heads.append((m.start(), m.end(), key))
    if dft != -1:
        for m in DISP.finditer(flat, dft):
            heads.append((m.start(), m.end(), 'dft-%02d' % (ORD.index(m.group(1).upper()) + 1)))
    out = []
    for i, (a, b, key) in enumerate(heads):
        e = heads[i + 1][0] if i + 1 < len(heads) else len(flat)
        ns = [n for off, n in notes_at if b <= off <= e]
        out.append((key, flat[b:e], ns))
    return out


def words(s: str) -> list[str]:
    s = s.replace('º', '°').replace('\xad', '')
    s = re.sub(r'\bN\s*°', ' ', s)
    return re.findall(r'\w+', s.lower())


if __name__ == '__main__':
    sys.path.insert(0, str(HERE.parent))
    import fetch
    segs = segments(fetch.path_for(url(sys.argv[1])))
    print(len(segs))
    d = {}
    for k, t, n in segs:
        d.setdefault(k, (t, n))
    for k in sys.argv[2:]:
        print(k, d.get(k))
