"""Amendments to the Código de Protección y Defensa del Consumidor after the third official edition (27 Nov 2020),
replayed from the laws' own texts.

The texts are Congreso's ADLP transcriptions ("PUBLICADA EL … EN EL DIARIO OFICIAL EL PERUANO"), which have a text
layer. Each law quotes the new wording between “ and ”; "[…]" marks wording left as it was. The operations below
only say WHERE each quoted paragraph goes; every word comes from the cached PDF. Paragraphs are rebuilt from the
PDF lines: a line that stops short of the right margin ends a paragraph, and so does a numbered item.

Check: Editora Peru's Normas Legales Actualizadas (Wayback capture 2024-08-19) is compared word for word with the
rebuilt text on its date. (The SPIJ export Indecopi publishes on gob.pe, April 2025, was used only to find the laws:
its text interleaves notes and older wording and is not compared.)
"""
from __future__ import annotations

import hashlib
import re

import fitz

import fetch
from edition import HEAD, clean_par, label_of

fitz.TOOLS.mupdf_display_errors(False)

ADLP = 'https://www.leyes.congreso.gob.pe/Documentos/%s/ADLP/Texto_Consolidado/%s-TXM.pdf'
ELLIPSIS = re.compile(r'^\[\s*(?:…|\.\.\.|\?)\s*\]\.?$')

# law, folder, published, in force, how, operations
#   ('whole', unit key, article)              the article as quoted (no […] allowed)
#   ('replace', unit key, article, label)     the labelled block as quoted replaces the current one
#   ('insert_after', unit key, article, after label, new label)
LAWS = [
    ('31207', '2016_2021', '2021-06-02', '2021-06-03', None, [
        ('insert_after', 'art-066', '66', ('num', '66.7'), ('num', '66.8')),
    ]),
    ('31435', '2021_2026', '2022-03-22', '2022-05-21',
     'Primera Disposición Complementaria Final: in force 60 calendar days counted from the day after publication', [
         ('replace', 'art-024', '24', ('num', '24.1')),
         ('whole', 'art-152', '152'),
     ]),
    ('31467', '2021_2026', '2022-05-06', '2022-05-07', None, [
        ('whole', 'art-147-a', '147-A'),
    ]),
    ('31537', '2021_2026', '2022-07-28', '2022-07-29', None, [
        ('replace', 'art-047', '47', ('lit', 'e')),
        ('insert_after', 'art-047', '47', ('lit', 'e'), ('lit', 'f')),
    ]),
    ('31601', '2021_2026', '2022-11-05', '2022-11-06', None, [
        ('insert_after', 'art-001', '1', ('lit', 'k'), ('lit', 'l')),
    ]),
    ('31763', '2021_2026', '2023-06-04', '2023-08-29',
     'Primera Disposición Complementaria Final: in force 60 business days counted from the day after publication '
     '(counted Monday to Friday from 5 June 2023, leaving out the national holidays of 29 June and 28 July 2023)', [
         ('replace', 'art-088', '88', ('num', '88.1')),
     ]),
    ('31937', '2021_2026', '2023-11-18', '2023-11-19', None, [
        ('insert_after', 'art-066', '66', ('num', '66.8'), ('num', '66.9')),
    ]),
    ('32032', '2021_2026', '2024-05-18', '2024-05-19', None, [
        ('insert_after', 'art-066', '66', ('num', '66.9'), ('num', '66.10')),
    ]),
    ('32230', '2021_2026', '2025-01-08', '2025-01-09', None, [
        ('replace', 'art-029', '29', ('lit', 'c')),
        ('replace', 'art-029', '29', ('lit', 'h')),
        ('replace', 'art-136', '136', ('lit', 'g')),
        ('replace', 'art-136', '136', ('lit', 'j')),
        ('whole', 'art-029-a', '29-A'),
    ]),
    ('32323', '2021_2026', '2025-05-09', '2025-05-10', None, [
        ('replace', 'art-058', '58', ('lit', 'e')),
        ('insert_after', 'art-058', '58', ('num', '58.2'), ('num', '58.3')),
    ]),
    ('32327', '2021_2026', '2025-05-10', '2025-05-11',
     'its Única Disposición Complementaria Final defers only the articles it adds to Ley 28587; its change to the '
     'Code (art. 2) takes effect the day after publication', [
         ('replace', 'art-042', '42', ('num', '42.3')),
     ]),
    ('32495', '2021_2026', '2025-11-11', '2025-11-12', None, [
        ('whole', 'art-150', '150'),
        ('whole', 'art-151', '151'),
    ]),
]


def url_of(n, folder):
    return ADLP % (folder, n)


def law_lines(path):
    """[(text, ends_paragraph)] for the PDF's lines; a line ends a paragraph when it stops well short of the
    page's right margin."""
    doc = fitz.open(str(path))
    out = []
    for page in doc:
        ls = []
        for blk in page.get_text('dict')['blocks']:
            for l in blk.get('lines', []):
                t = ''.join(sp['text'] for sp in l['spans'])
                if not t.strip():
                    continue
                ls.append((l['bbox'][3], l['bbox'][0], t.strip(), l['bbox'][2]))
        if not ls:
            continue
        # some transcriptions set each word of a justified line as its own text line: regroup by baseline
        rows: list[list] = []
        for it in sorted(ls):
            if rows and abs(rows[-1][0][0] - it[0]) < 2.5:
                rows[-1].append(it)
            else:
                rows.append([it])
        right = max(it[3] for it in ls)
        for row in rows:
            row.sort(key=lambda it: it[1])
            out.append((' '.join(it[2] for it in row), max(it[3] for it in row) < right - 45))
    return out


def title_of(lines) -> str:
    ts = [t for t, _ in lines]
    i = next(i for i, t in enumerate(ts) if t.startswith('LEY QUE') or t.startswith('LEY DE'))
    out = []
    while i < len(ts) and not re.fullmatch(r'LEY \d+', ts[i]):
        out.append(ts[i])
        i += 1
    return ' '.join(out)


ART = re.compile(r'^Art[íi]culo\s+(\d+(?:-[A-Z])?)\s*\.(?:-)?\s')


def quoted_articles(lines) -> dict[str, list[str]]:
    """Article number -> quoted paragraphs ('[…]' kept as a marker). A full stop printed after the closing quote
    (Spanish style) belongs to the last quoted sentence and is restored."""
    text = ''.join(t + ('\n' if end else ' ') for t, end in lines)
    out: dict[str, list[str]] = {}
    for m in re.finditer(r'“(.*?)”(\.?)', text, re.S):
        cur = None
        paras: list[str] = []
        # split on paragraph ends, and before labels / ellipses / headings that start a line run
        chunks = []
        for para in m.group(1).split('\n'):
            para = para.strip()
            if not para:
                continue
            # an ellipsis or a label glued to the end of the previous line run starts a new paragraph
            parts = re.split(r'\s(?=\[(?:…|\.\.\.|\?)\]\s)|(?<=\])\s(?=\S)|\s(?=(?:\d{1,3}(?:\.\d{1,3})+\.?|[a-z]\)|[a-z]\.)\s+[A-ZÁÉÍÓÚ])',
                             para)
            chunks.extend(p.strip() for p in parts if p and p.strip())
        for c in chunks:
            a = ART.match(c)
            if a:
                if cur is not None:
                    out[cur] = paras
                cur = a.group(1)
                paras = [c]
                continue
            if cur is None:
                continue
            paras.append(c)
        if cur is not None:
            if m.group(2) and paras and not ELLIPSIS.match(paras[-1]) and not re.search(r'[.;:]$', paras[-1]):
                paras[-1] += '.'
            out[cur] = paras
    return {k: [clean_par(p) for p in v] for k, v in out.items()}


def _block(paras, i):
    """End (exclusive) of the labelled block at i: a numeral runs over its literals and unlabelled paragraphs up to
    the next numeral; a literal is its own paragraph."""
    lab = label_of(paras[i])
    if lab[0] != 'num':
        return i + 1
    e = i + 1
    while e < len(paras) and (label_of(paras[e]) is None or label_of(paras[e])[0] != 'num'):
        e += 1
    return e


def _find(paras, lab):
    hits = [i for i, p in enumerate(paras) if i and label_of(p) == lab]
    if len(hits) != 1:
        raise SystemExit(f'label {lab}: {len(hits)} matches in {paras[0][:60]!r}')
    return hits[0]


def _quoted_block(q, lab, art, n):
    i = next((i for i, p in enumerate(q) if label_of(p) == lab), None)
    if i is None:
        raise SystemExit(f'Ley {n}: art. {art} quotes no {lab}: {q}')
    e = _block(q, i)
    while e > i + 1 and ELLIPSIS.match(q[e - 1]):
        e -= 1
    blk = [p for p in q[i:e] if not ELLIPSIS.match(p)]
    if len(blk) != e - i:
        raise SystemExit(f'Ley {n}: art. {art} {lab} has […] inside')
    return blk


def apply(state: dict, log: list[str]) -> list[dict]:
    """Replays LAWS on state (key -> unit dict), updating it. Returns one dict per law."""
    out = []
    for n, folder, pub, day, how, ops in LAWS:
        url = url_of(n, folder)
        path = fetch.cached(url)
        if path is None:
            raise SystemExit(f'not in the cache: {url}')
        lines = law_lines(path)
        q = quoted_articles(lines)
        changes = {}
        for op in ops:
            kind, key, art = op[0], op[1], op[2]
            if art not in q:
                raise SystemExit(f'Ley {n}: no quoted art. {art} (have {sorted(q)})')
            src = q[art]
            if kind == 'whole':
                if any(ELLIPSIS.match(p) for p in src):
                    raise SystemExit(f'Ley {n}: art. {art} quoted with […] but used whole')
                new = list(src)
            else:
                cur = [l for l in (changes.get(key) or state[key])['text'].split('\n') if l]
                if kind == 'replace':
                    i = _find(cur, op[3])
                    e = _block(cur, i)
                    new = cur[:i] + _quoted_block(src, op[3], art, n) + cur[e:]
                elif kind == 'insert_after':
                    i = _find(cur, op[3])
                    e = _block(cur, i)
                    new = cur[:e] + _quoted_block(src, op[4], art, n) + cur[e:]
                else:
                    raise SystemExit(kind)
            if key in state:
                label, ukind = state[key]['label'], state[key]['kind']
            else:
                m = HEAD.match(new[0])
                base, suf = m.group(1), m.group(2)
                label, ukind = 'Art. %s' % (base + ('-' + suf if suf else '')), 'art'
            changes[key] = {'label': label, 'kind': ukind, 'text': ''.join(p + '\n' for p in new)}
        # every quoted paragraph used must occur word for word in the law's text
        flat = clean_par(' '.join(' '.join(t for t, _ in lines).split()))
        for key, u in changes.items():
            old = (state.get(key) or {}).get('text', '')
            for p in u['text'].split('\n'):
                if p and p + '\n' not in old and ' '.join(p.split()).rstrip('.') not in flat:
                    raise SystemExit(f'Ley {n}: paragraph not found word for word in the law: {p[:120]}')
        for key, u in changes.items():
            state[key] = u
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        title = title_of(lines)
        out.append({
            'key': f'ley-{n}', 'in_force': day, 'url': url, 'sha256': sha, 'changes': changes,
            'vnote': f'Wording of Ley {n} from {url}.',
            'law': {'label': f'Ley {n}', 'title': title, 'kind': 'law', 'enacted': None, 'published': pub,
                    'url': url, 'temporary_until': None, 'restores': None, 'note': None},
        })
        log.append(f'Ley {n}: in force {day} ({how or "the day after publication, Constitución art. 109"}); '
                   f'changes {sorted(changes)}')
    return out


def sources() -> list[dict]:
    return [{'name': f'Congreso, Archivo Digital de la Legislación del Perú: Ley {n} (texto publicado en El Peruano)',
             'url': url_of(n, folder), 'retrieved': '2026-10-29', 'requests': 1,
             'licence': 'Official text (Peruvian legal norms are not subject to copyright, D.Leg. 822 art. 9)',
             'notes': 'text layer; amends the Code after the third official edition'}
            for n, folder, *_ in LAWS] + [
        {'name': 'Congreso law index (LeyNumePP.aspx), searched by title ("CONSUMIDOR") and by number 32231-32550',
         'url': 'https://www.leyes.congreso.gob.pe/LeyNumePP.aspx?xNorma=0', 'retrieved': '2026-10-29',
         'requests': 18, 'licence': 'as above',
         'notes': 'titles; ends at Ley 32537 (26 Dec 2025); no decretos legislativos'},
        {'name': 'Editora Perú, Normas Legales Actualizadas: Código de Protección y Defensa del Consumidor '
                 '(idNorma=17); Internet Archive capture 2024-08-19 05:16:28 UTC',
         'url': NLA, 'retrieved': '2026-10-29', 'requests': 1,
         'licence': 'Editora Perú publication; archive.org capture', 'notes': 'checkpoint only'},
        {'name': 'Indecopi on gob.pe: Ley 29571 as exported from SPIJ (MINJUS), uploaded April 2025',
         'url': SPIJ, 'retrieved': '2026-10-29', 'requests': 1,
         'licence': 'Official text (Peruvian legal norms are not subject to copyright, D.Leg. 822 art. 9)',
         'notes': 'used only to find the amending laws to April 2025; its text interleaves notes and older wording'},
    ]


DECISIONS = [
    'After the third official edition (27 November 2020) the Code\'s amendments are replayed from the laws\' own '
    'texts (Congreso ADLP transcriptions, text layer): Leyes 31207, 31435, 31467, 31537, 31601, 31763, 31937, '
    '32032, 32230, 32323, 32327 and 32495. They were found in the amendment notes of Editora Perú\'s Normas '
    'Legales Actualizadas (August 2024) and of the SPIJ text Indecopi publishes (April 2025), and in the Congreso '
    'law index by title up to Ley 32537 (26 December 2025). Every paragraph a law brings is checked to occur word '
    'for word in that law\'s text; "[…]" keeps the existing wording.',
    'Ley 31435 is in force 60 calendar days counted from the day after publication (its Primera Disposición '
    'Complementaria Final): 21 May 2022, counted like the Code\'s own 30 days (day 1 = the day after publication).',
    'Ley 31763 is in force 60 business days counted from the day after publication (its Primera Disposición '
    'Complementaria Final). No official source found gives the day; it is counted Monday to Friday from 5 June '
    '2023, leaving out the national holidays of 29 June and 28 July 2023, which gives 29 August 2023. Days declared '
    'non-working for the public sector are not left out; if any applies, the true day is a little later.',
    'Ley 32327: only the articles it adds to Ley 28587 wait 90 days; its change to art. 42.3 of the Code takes '
    'effect the day after publication (11 May 2025).',
    'Ley 32323 quotes the heading "Capítulo II Métodos comerciales agresivos o engañosos" before art. 58; structure '
    'headings are not tracked, so it is not used.',
    'Checkpoint nla-2024-08 explained: art. 88 differs because Editora Perú had not yet inserted Ley 31763 (its '
    'own note says the change "se insertará ... cuando entre en vigencia"); Título Preliminar art. V reads '
    '"carácterísticas" in both MINJUS editions (2018, 2020) and "características" in Editora Perú\'s text; the '
    'editions\' spelling is kept. The final dispositions are not compared (the NLA text is cut at its headings).',
    'Not found, so not in this history: decretos legislativos and laws whose title does not name the Code after '
    'April 2025 (the SPIJ text), and anything after Ley 32537 (26 December 2025), where the Congreso index ends. '
    'Today\'s text may lack such changes.',
]

NLA = 'https://web.archive.org/web/20240819051628id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=17'
SPIJ = 'https://cdn.www.gob.pe/uploads/document/file/1351847/1244218-ley-29571_spij.pdf?v=1745616997'


def _words(t: str) -> str:
    t = re.sub(r'(Art[íi]culo\s+[IVXL\d]+)\s*[°º˚]', r'\1', t)
    t = t.replace('núm.', 'Nº').replace('N°', 'Nº')
    return ' '.join(re.findall(r'\w+', t.lower()))


def _split_articles(t: str, start: str, end: str | None) -> dict[str, str]:
    """Word strings by unit key from a running text of the Code (headings 'Artículo N.- …')."""
    i = t.find(start)
    m = re.compile(re.escape(end), re.I).search(t, i) if end else None
    j = m.start() if m else len(t)
    body = t[i:j]
    out = {}
    marks = list(re.finditer(r'(?:(?<=\s)|^)[“"]?(Art[íi]culo\s+([IVXL]+|\d+(?:-[A-Z])?)\s*[°º]?\.\s*-?)\s', body))
    for a, b in zip(marks, marks[1:] + [None]):
        num = a.group(2)
        seg = body[a.start():b.start() if b else len(body)]
        if re.fullmatch(r'[IVXL]+', num):
            from edition import roman
            key = 'tp-%02d' % roman(num)
        else:
            base, _, suf = num.partition('-')
            key = 'art-%03d%s' % (int(base), '-' + suf.lower() if suf else '')
        if key in out:
            continue        # a quoted older text of the same article
        out[key] = seg
    return out


def _clean_nla(seg: str) -> str:
    seg = re.sub(r'\(\*\)[^“]*?(?:\d{4}\.|(?=“))', ' ', seg)        # amendment notes
    seg = re.sub(r'CONCORDANCIAS?:.*?(?=“|$)', ' ', seg)
    seg = re.sub(r'\d+ Inicio NORMAS LEGALES ACTUALIZADAS (?:Código de Protección y Defensa del Consumidor ?){1,2}',
                 ' ', seg, flags=re.I)
    seg = re.sub(r'\s(?:TÍTULO [IVX]+|Capítulo [IVX]+|Subcapítulo [IVX]+|DISPOSICIONES COMPLEMENTARIAS)\b[^.]*$', ' ',
                 seg, flags=re.I)
    return seg


def nla_units() -> dict[str, str]:
    p = fetch.CACHE / hashlib.sha256(NLA.encode('utf-8')).hexdigest()
    if not p.exists():
        return {}
    d = fitz.open(str(p))
    t = ' '.join(''.join(pg.get_text() for pg in d).split())
    arts = _split_articles(t, 'Artículo I.- Contenido', 'DISPOSICIONES COMPLEMENTARIAS FINALES PRIMERA')
    return {k: _words(_clean_nla(v)) for k, v in arts.items()}


def spij_units() -> dict[str, str]:
    p = fetch.cached(SPIJ)
    if p is None:
        return {}
    d = fitz.open(str(p))
    t = ' '.join(''.join(pg.get_text() for pg in d).split())
    arts = _split_articles(t, 'Artículo I.- Contenido', 'DISPOSICIONES COMPLEMENTARIAS FINALES PRIMERA')
    return {k: _words(_clean_nla(v)) for k, v in arts.items()}


CHECKS = {
    'nla-2024-08': ('2024-08-15', nla_units),
}
