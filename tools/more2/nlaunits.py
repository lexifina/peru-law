"""Units (provisions) of an act from Editora Perú's Normas Legales Actualizadas PDF.

The body is read span by span with its position; running heads and the bold-italic amendment notes are dropped.
A paragraph ends where a line ends short of the column's right edge after a full stop, colon or semicolon, or where
the next line starts a labelled item. Provisions start at "Artículo N.-" (Título Preliminar in roman numerals) and at
the complementary provisions; structure headings (LIBRO, TÍTULO, CAPÍTULO, SECCIÓN and other all-capital lines) are
not units. The quotation marks Editora Perú puts around amended wording are removed.

    python -X utf8 more2/nlaunits.py ID TS [KEY ...]       print units (debugging)
"""
from __future__ import annotations

import hashlib
import re
import sys
import unicodedata
from pathlib import Path

import fitz

fitz.TOOLS.mupdf_display_errors(False)
HERE = Path(__file__).resolve().parent
CACHE = HERE.parent / '.cache'
URL = 'https://web.archive.org/web/{ts}id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma={id}'
ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
ORD = ['PRIMERA', 'SEGUNDA', 'TERCERA', 'CUARTA', 'QUINTA', 'SEXTA', 'SÉPTIMA', 'OCTAVA', 'NOVENA', 'DÉCIMA']


def roman(s: str) -> int:
    n = 0
    for a, b in zip(s, s[1:] + ' '):
        v = ROMAN[a]
        n += -v if b != ' ' and ROMAN[b] > v else v
    return n


def norm(s: str) -> str:
    s = unicodedata.normalize('NFC', s).replace('﻿', '').replace('​', '')
    for a in ('\xa0', ' ', ' ', ' ', '\t'):
        s = s.replace(a, ' ')
    return s


def path(nid, ts) -> Path:
    return CACHE / hashlib.sha256(URL.format(id=nid, ts=ts).encode('utf-8')).hexdigest()


def rows(doc):
    """[(column, text, x0, x1, right_edge)] in reading order; notes removed."""
    out = []
    for pn in range(doc.page_count):
        page = doc[pn]
        mid = page.rect.width / 2
        spans = []
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                for s in l['spans']:
                    f = s['font']
                    if f.startswith(('StagSans', 'MyriadPro')) or s['size'] < 7.5:
                        continue
                    if 'Italic' in f and 'Bold' in f:          # amendment notes
                        continue
                    if not s['text'].strip():
                        continue
                    col = 0 if s['bbox'][0] < mid - 5 else 1
                    spans.append((col, round(s['origin'][1], 1), s['bbox'][0], s['bbox'][2], norm(s['text']), 'Bold' in f))
        spans.sort()
        grp = []
        for sp in spans:
            if grp and grp[-1][0][0] == sp[0] and abs(grp[-1][0][1] - sp[1]) < 2.0:
                grp[-1].append(sp)
            else:
                grp.append([sp])
        right = {}
        for g in grp:
            right[g[0][0]] = max(right.get(g[0][0], 0), max(s[3] for s in g))
        for g in grp:
            g.sort(key=lambda s: s[2])
            text = ''.join(s[4] for s in g)
            out.append((g[0][0], text, g[0][2], max(s[3] for s in g), right[g[0][0]], all(s[5] for s in g), g[0][1]))
    return out


LABEL = re.compile(r'^[“"]?(?:[a-zñ]\)|[a-zñ]\.\s|\d+(?:\.\d+)*\.\s|\d+\)|[IVX]+\.\s|Art[íi]culo\s|[A-ZÁÉÍÓÚ]{3,}[\s.]|•|-\s)')
ITEM = re.compile(r'^[“"]?(?:[a-zñ]\)|\d+(?:\.\d+)*\.\s|\d+\))')
HEAD = re.compile(r'^[“"]?\s*Art[íi]culo\s+(?:(?P<r>[IVXL]+)(?:-(?P<rs>[A-Z])\b)?|(?P<n>\d+)(?:\s*-?\s*(?P<s>[A-Z])\b)?)(?:\s+del\s+T[íi]tulo\s+Preliminar|\s+T[íi]tulo\s+Preliminar)?\s*[°º]?\s*\.?-?')
DISP = re.compile(r'^[“"]?\s*(?P<o>PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]PTIMA|OCTAVA|NOVENA|D[ÉE]CIMA|[ÚU]NICA)\b'
                  r'(?:\s+Disposici[óo]n\s+Complementaria)?\s*\.?-', re.I)
HSTRICT = re.compile(r'^[“"]?\s*Art[íi]culo\s+(?:[IVXL]+|\d+(?:\s*-?\s*[A-Z])?)(?:\s+(?:del\s+)?T[íi]tulo\s+Preliminar)?\s*[°º]?\s*(?:\.?\s*-|\.\s+(?=[A-ZÁÉÍÓÚ])|\.?$)')
DSTRICT = re.compile(r'^[“"]?\s*(?:PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]PTIMA|OCTAVA|NOVENA|D[ÉE]CIMA|[ÚU]NICA|Primera|Segunda|Tercera|Cuarta|Quinta)(?:\s+Disposici[óo]n\s+Complementaria)?\s*\.-')
STRUCT = re.compile(r'^[“"]?(LIBRO|T[ÍI]TULO|CAP[ÍI]TULO|SECCI[ÓO]N|SUBCAP[ÍI]TULO)\b')


def paragraphs(rs, bold_breaks: bool = False, ord_breaks: bool = False) -> list[str]:
    paras, cur, prev, pbold, py = [], '', None, False, None
    for col, text, x0, x1, right, bold, y in rs:
        t = text.strip()
        brk = False
        if prev is not None:
            pt, px1, pright = prev
            short = px1 < pright - 25
            if bold_breaks and bold != pbold:
                brk = True          # an all-bold line (epigraph, heading) is a paragraph of its own
            elif bold_breaks and bold and pbold and not HSTRICT.match(t):
                gap = (y - py) if py is not None and y > py else 99
                brk = gap > 13 or bool(STRUCT.match(t) or STRUCT.match(pt))
            elif short and re.search(r'[.:;”"]\s*$', pt):
                brk = True
            elif LABEL.match(t) and re.search(r'[.:;”"]\s*$', pt):
                brk = True
            elif STRUCT.match(t) or STRUCT.match(pt):
                brk = True
            elif t.upper() == t and re.search(r'[A-ZÁÉÍÓÚ]{4}', t) and short:
                brk = True
            elif ITEM.match(t) and (short or ITEM.fullmatch(cur.strip())):
                brk = True
            elif ord_breaks and ORDH.match(t) and ordinal(ORDH.match(t).group(1)) and re.search(r'[.:;”"]\s*$', pt):
                brk = True          # "Sexta.- ...", "Undécima- ...": a disposition after a full stop (opt-in)
            elif HSTRICT.match(t) or DSTRICT.match(t):
                brk = True
            elif pt.upper() == pt and re.search(r'[A-ZÁÉÍÓÚ]{4}', pt) and not re.search(r'[a-záéíóúñ]', pt):
                brk = True
            elif short and HSTRICT.match(cur):
                brk = True          # the end of a heading line ("Artículo 74.- Deberes y derechos de los padres.-")
        if brk or cur == '':
            if cur:
                paras.append(cur)
            cur = t
        else:
            if cur.endswith('\xad') or (cur.endswith('-') and not cur.endswith(' -')):
                cur = cur.rstrip('\xad')
                cur = cur[:-1] + t if cur.endswith('-') and re.search(r'[a-záéíóúñ]-$', cur) and t[:1].islower() else cur + t
            else:
                cur = cur + ' ' + t
        prev = (t, x1, right)
        pbold, py = bold, y
    if cur:
        paras.append(cur)
    return [' '.join(p.split()) for p in paras]


def unquote(p: str) -> str:
    p = re.sub(r'\s*\(\*+\)\s*$', '', p)
    p = re.sub(r'^\(\*+\)\s*', '', p)
    if p[:1] in '“"':
        p = p[1:].lstrip()
    if p.endswith(('”', '".', '”.', '"')):
        p = re.sub(r'[”"]\.?$', '', p).rstrip()
        if not p.endswith(('.', ':', ';')):
            p += '.' if False else ''
    return p


ORDW = {'primera': 1, 'segunda': 2, 'tercera': 3, 'cuarta': 4, 'quinta': 5, 'sexta': 6, 'séptima': 7, 'septima': 7,
        'sétima': 7, 'octava': 8, 'novena': 9, 'décima': 10, 'decima': 10, 'undécima': 11, 'duodécima': 12,
        'decimotercera': 13, 'decimocuarta': 14, 'decimoquinta': 15, 'decimosexta': 16, 'decimoséptima': 17,
        'decimoctava': 18, 'decimonovena': 19, 'vigésima': 20, 'vigesimoprimera': 21, 'vigesimosegunda': 22,
        'vigesimotercera': 23, 'vigesimocuarta': 24, 'vigesimoquinta': 25, 'única': 1, 'unica': 1}
DNAMED = re.compile(r'^[“"]?(?P<o>[A-Za-zÁÉÍÓÚáéíóú]+)\s+Disposici[óo]n\s+(?P<t>Complementaria\s+Transitoria|Complementaria\s+Final|'
                    r'Transitoria|Final|Complementaria)\s*(?:\.?\s*-)?\s*(?P<rest>.*)$')
DKEY = {'transitoria': 'dt', 'final': 'df', 'complementaria transitoria': 'dct', 'complementaria final': 'dcf',
        'complementaria': 'dc'}

UNITS_ORD = {'primera': 1, 'primero': 1, 'segunda': 2, 'segundo': 2, 'tercera': 3, 'tercero': 3, 'cuarta': 4, 'cuarto': 4,
             'quinta': 5, 'quinto': 5, 'sexta': 6, 'sexto': 6, 'septima': 7, 'septimo': 7, 'setima': 7, 'setimo': 7,
             'octava': 8, 'octavo': 8, 'novena': 9, 'noveno': 9}
TENS = {'decima': 10, 'decimo': 10, 'vigesima': 20, 'vigesimo': 20, 'trigesima': 30, 'trigesimo': 30,
        'cuadragesima': 40, 'cuadragesimo': 40, 'quincuagesima': 50, 'quincuagesimo': 50,
        'sexagesima': 60, 'sexagesimo': 60, 'septuagesima': 70, 'septuagesimo': 70, 'octogesima': 80, 'octogesimo': 80,
        'nonagesima': 90, 'nonagesimo': 90}
SPECIAL = {'undecima': 11, 'undecimo': 11, 'duodecima': 12, 'duodecimo': 12, 'unica': 1, 'unico': 1}
SECTION = re.compile(r'^[“"]?DISPOSICI[OÓ]N(?:ES)?\s+(?:COMPLEMENTARIAS?\s+)?(FINAL(?:ES)?|TRANSITORIAS?|DEROGATORIAS?|'
                     r'MODIFICATORIAS?|COMPLEMENTARIAS?)(?![A-Z])')
SECKEY = {'FINAL': 'dcf', 'TRANSITORIA': 'dct', 'DEROGATORIA': 'dcd', 'MODIFICATORIA': 'dcm', 'COMPLEMENTARIA': 'dc'}


def ordinal(text: str):
    """(number, words used) for a Spanish feminine/masculine ordinal at the start of text, else None."""
    t = unicodedata.normalize('NFD', text.lower())
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    m = re.match(r'^[“"]?\s*([a-z]+)(?:\s+([a-z]+))?', t)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    if a in SPECIAL:
        return SPECIAL[a]
    if a in UNITS_ORD:
        return UNITS_ORD[a]
    for k, v in TENS.items():
        if a == k:
            return v + (UNITS_ORD.get(b, 0) if b else 0)
        if a.startswith(k) and a[len(k):] in UNITS_ORD:
            return v + UNITS_ORD[a[len(k):]]
    return None


ORDH2 = re.compile(r'^[“"]?\s*([A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóú]+)?)\s*\.?\s*-(?:\s|$|(?=[A-ZÁÉÍÓÚ]))')
ORDDOT = re.compile(r'^[“"]?\s*([A-ZÁÉÍÓÚ][a-záéíóú]+(?:-[a-záéíóú]+)?)\.[\xad\s]')
NORMA = re.compile(r'^[“"]?\s*NORMA\s+([IVXL]+)\s*:')
ORDH = re.compile(r'^[“"]?\s*([A-ZÁÉÍÓÚ][a-záéíóú]+)\s*\.?\s*-\s*\S')
ORDHEAD = re.compile(r'^[“"]?\s*((?:[A-ZÁÉÍÓÚ][a-záéíóú]+)(?:\s+[A-Za-záéíóú]+)?)\s*\.\s*-?\s*(.*)$')


def units(nid, ts, start_marker='TÍTULO PRELIMINAR', end_marker=r'^Comuníquese', disp_prefix='dc', sumillas=False, bold_breaks=False,
          notes=None, drop=None, ord_heads=False, disp_label='complementaria', quoted_in_disp=False,
          norma_heads=False, fn_markers=False, ord_heads2=False, caps_heads=False, arts_in_disp=False, drop2=None, annex=False,
          tp_re=None, subs=(), drop_units=(), ord_dot=False, sec_first=False, ord_suffix=False, split_at=(), join_next=()):
    doc = fitz.open(str(path(nid, ts)))
    ps = paragraphs(rows(doc), bold_breaks, ord_heads)
    for a, b in subs:          # (opt-in) hand corrections of the text layer, listed in the spec ("Artículo1.")
        ps = [re.sub(a, b, p) for p in ps]
    for rx in split_at:        # (opt-in) paragraph breaks the layout hides (a full line ending in a closing quote,
        ps = [q for p in ps for q in re.split(rx, p)]      # list items set two to a line), listed in the spec
    for rx in join_next:       # (opt-in) a paragraph the layout breaks in two (a bold lead-in): joined to the next one
        ps2 = []
        for p in ps:
            if ps2 and ps2[-1] is not None and re.search(rx, ps2[-1]):
                ps2[-1] = ps2[-1] + ' ' + p
                continue
            ps2.append(p)
        ps = ps2
    if notes or drop or drop2:
        # files whose amendment notes are set in the body font: "notes" strips a leading note from a paragraph,
        # "drop" removes whole paragraphs (Editora Perú's "(*) ... se incluirá" notices), "drop2" a paragraph and the
        # one after it (a numbered structure heading and its name: "Subcapítulo 2" / "Título supletorio ...")
        ps2 = []
        skip = False
        for p in ps:
            if skip:
                skip = False
                continue
            if drop2 and re.match(drop2, p):
                skip = True
                continue
            if drop and re.match(drop, p):
                continue
            for q in (re.split(notes, p) if notes else [p]):     # a note between two paragraphs also ends the first
                if q and q.strip():
                    ps2.append(q.strip())
        ps = ps2
    # the body starts at the second "TÍTULO PRELIMINAR" (the first is in the table of contents)
    idx = [i for i, p in enumerate(ps) if p.strip('“"') == start_marker]
    if idx:
        i0 = idx[1] if len(idx) > 1 else idx[0]
    else:
        i0 = next(i for i, p in enumerate(ps) if HSTRICT.match(p)) - 1
    out, cur, pend = {}, None, None
    body = ps[i0 + 1:]
    after_struct = False
    section = None
    in_quote = False
    sec_full = ''
    for j, p in enumerate(body):
        if re.match(end_marker, p):
            break
        if bold_breaks:
            if after_struct and not HSTRICT.match(p) and not DNAMED.match(p) and p.upper() != p:
                after_struct = False
                continue            # the name of the chapter or section just announced
            after_struct = bool(STRUCT.match(p)) or (after_struct and p.upper() == p)
            if sec_first and after_struct and SECTION.match(p) and p.upper() == p:
                after_struct = False    # (opt-in) "TÍTULO V / DISPOSICIONES FINALES / Primera.- ...": no name follows
        if p.startswith('¿DESEAS'):
            continue                # Editora Perú's advertisement
        if fn_markers:
            p = re.sub(r'\(\d{1,3}\)(?=[A-Za-zÁÉÍÓÚáéíóúÑñ“"])', '', p)    # (opt-in) footnote numbers run into the text
        if annex and re.match('^ANEXOS?(?: [IVX0-9]+)?$', p):
            n = sum(1 for k in out if k.startswith('anexo')) + 1      # (opt-in) the law's annex, one unit
            cur = 'anexo-%02d' % n
            out[cur] = {'label': 'Anexo' + (' %d' % n if n > 1 else ''), 'kind': 'provision', 'lines': [p]}
            continue
        if annex and cur and cur.startswith('anexo'):
            out[cur]['lines'].append(unquote(p))
            continue
        if (caps_heads and cur and cur.startswith('art-') and len(out[cur]['lines']) == 1 and p.upper() == p
                and re.search('[A-ZÁÉÍÓÚ]{3}', p) and not STRUCT.match(p) and not SECTION.match(p)
                and not re.search(r'[.:;]\s*$', out[cur]['lines'][0])):
            # (opt-in) an all-capital epigraph the page break split ("... EN EL FLUJO" / "DE INGRESOS Y EGRESOS ...")
            out[cur]['lines'][0] = out[cur]['lines'][0] + ' ' + p
            continue
        if tp_re and re.match(tp_re, p) and not any(k.startswith('art-') for k in out):
            r = re.match(tp_re, p).group(1)      # (opt-in) principles of a Título Preliminar ("I. PRINCIPIO DE ...")
            cur = 'tp-%02d' % roman(r)
            out[cur] = {'label': f'Título Preliminar, {r}', 'kind': 'art', 'lines': [unquote(p)]}
            continue
        if norma_heads and NORMA.match(p):
            r = NORMA.match(p).group(1)
            cur = 'tp-%02d' % roman(r)          # (opt-in) the Normas of a Título Preliminar ("NORMA I: CONTENIDO")
            out[cur] = {'label': f'Título Preliminar, norma {r}', 'kind': 'art', 'lines': [unquote(p)]}
            continue
        if ord_heads2 and section:
            mo = ORDH2.match(p)
            if not mo and ord_dot:
                mo = ORDDOT.match(p)     # (opt-in) "Primera. Los ...", "Segunda.­ ...", "Décimo-primera. ..."
            n = ordinal(mo.group(1).replace('-', ' ')) if mo else None
            if n:              # (opt-in) every disposition after a section heading, one- or two-word ordinals
                fin, tra = 'FINAL' in sec_full, 'TRANSITORIA' in sec_full
                comp = 'COMPLEMENTARIA' in sec_full
                mod, der = 'MODIFICATORIA' in sec_full, 'DEROGATORIA' in sec_full
                pre = ('dc' if comp else 'd') + ('ft' if fin and tra else 'f' if fin else 't' if tra else
                                                  'm' if mod else 'd' if der else '')
                lab = ' '.join(x for x in ('complementaria' if comp else '',
                                           'final y transitoria' if fin and tra else 'final' if fin else
                                           'transitoria' if tra else 'modificatoria' if mod else
                                           'derogatoria' if der else '') if x)
                cur = '%s-%02d' % (pre, n)
                suf = re.match(r'^[“"]?\s*[A-ZÁÉÍÓÚ][a-záéíóú]+-([A-Z])\.?\s*-', p) if ord_suffix else None
                if suf:         # (opt-in) "Primera-A.- ..." -> dcf-01-a
                    cur += '-' + suf.group(1).lower()
                out[cur] = {'label': f'Disposición {lab} {mo.group(1).lower()}' + (f'-{suf.group(1)}' if suf else ''),
                            'kind': 'provision', 'lines': [unquote(p)]}
                continue
        if quoted_in_disp and cur and cur.split('-')[0] in ('dc', 'dcf', 'dct', 'dcm', 'dcd', 'dt', 'df'):
            # (opt-in) another law's articles quoted inside a disposition ("Sustitúyense los artículos ... por los
            # siguientes textos: “Artículo 326.- ...”") stay in the disposition; a line starting in lower case
            # continues the line before (a heading the layout broke)
            if in_quote or p.startswith('“'):
                in_quote = not re.search(r'[”"]\.?$', p)
                if p[:1].islower() and out[cur]['lines']:
                    out[cur]['lines'][-1] += ' ' + p
                else:
                    out[cur]['lines'].append(p)
                continue
        nxt = body[j + 1] if j + 1 < len(body) else ''
        if (HSTRICT.match(nxt) and not HSTRICT.match(p) and len(p) < 140 and not ITEM.match(p)
                and not re.search(r'[.:;”"]$', p) and (bold_breaks or (',' not in p and not p.endswith(','))) and p.upper() != p):
            pend = unquote(p) if sumillas else None    # an epigraph printed above the article it names
            continue
        m = DNAMED.match(p)
        if m and m.group('o').lower() in ORDW and not STRUCT.match(p):
            t = ' '.join(m.group('t').lower().split())
            cur = '%s-%02d' % (DKEY[t], ORDW[m.group('o').lower()])
            head = unquote(p)[:len(unquote(p)) - len(m.group('rest'))].strip() if m.group('rest') else unquote(p)
            out[cur] = {'label': f'Disposición {t} {m.group("o").lower()}', 'kind': 'provision', 'lines': [head]}
            if m.group('rest'):
                out[cur]['lines'].append(unquote(m.group('rest')))
            continue
        if (arts_in_disp and section and cur and cur.split('-')[0] in ('dc', 'dcf', 'dct', 'dcm', 'dcd', 'dt', 'df',
                                                                      'dft', 'dm', 'dd') and HEAD.match(p)):
            out[cur]['lines'].append(p)     # (opt-in) another code's articles, quoted inside a disposition
            continue
        m = HEAD.match(p)
        if m:
            if m.group('r'):
                rs = m.group('rs')      # "Artículo II-A" -> tp-02-a
                key = 'tp-%02d' % roman(m.group('r')) + ('-' + rs.lower() if rs else '')
                label = f'Título Preliminar, art. {m.group("r")}' + (f'-{rs}' if rs else '')
            else:
                n, s = int(m.group('n')), m.group('s')
                key = 'art-%03d%s' % (n, '-' + s.lower() if s else '')
                label = f'Art. {n}' + (f'-{s}' if s else '')
            cur = key
            out[key] = {'label': label, 'kind': 'art', 'lines': ([pend] if pend else []) + [unquote(p)]}
            pend = None
            continue
        if ord_heads and section:
            mo = ORDH.match(p)
            n = ordinal(mo.group(1)) if mo else None
            if n:              # every disposition after the section heading, any ordinal (opt-in)
                cur = '%s-%02d' % (disp_prefix, n)
                out[cur] = {'label': f'Disposición {disp_label} {mo.group(1).lower()}', 'kind': 'provision',
                            'lines': [unquote(p)]}
                continue
        m = DISP.match(p)
        if m and not STRUCT.match(p):
            o = m.group('o').upper().replace('SEPTIMA', 'SÉPTIMA').replace('DECIMA', 'DÉCIMA')
            n = 1 if o in ('ÚNICA', 'UNICA') else ORD.index(o) + 1
            cur = '%s-%02d' % (disp_prefix, n)
            out[cur] = {'label': f'Disposición complementaria {o.lower()}', 'kind': 'provision', 'lines': [unquote(p)]}
            continue
        ms = SECTION.match(p)
        if ms and p.upper() == p:
            section = SECKEY[re.sub(r'(?:ES|S)$', '', ms.group(1)).replace('FINAL', 'FINAL')]
            sec_full = p
            cur = None
            continue
        if section:
            mo = ORDHEAD.match(p)
            if mo:
                words = mo.group(1)
                n = ordinal(words)
                two = n is not None and ordinal(words.split()[0]) != n
                if n is None and len(words.split()) > 1:
                    n = ordinal(words.split()[0]); words = words.split()[0]
                    mo = re.match(r'^[“"]?\s*' + re.escape(words) + r'\s*\.\s*-?\s*(.*)$', p)
                    rest = mo.group(1) if mo else None
                else:
                    rest = mo.group(2)
                if n and rest is not None:
                    cur = '%s-%02d' % (section, n)
                    head = unquote(p)[:len(unquote(p)) - len(rest)].strip() if rest else unquote(p)
                    out[cur] = {'label': 'Disposición ' + {'dcf': 'complementaria final', 'dct': 'complementaria transitoria', 'dcm': 'complementaria modificatoria', 'dcd': 'complementaria derogatoria'}.get(section, 'complementaria') + ' ' + words.lower(), 'kind': 'provision', 'lines': [head]}
                    if rest:
                        out[cur]['lines'].append(unquote(rest))
                    continue
        if STRUCT.match(p) or (p.upper() == p and re.search(r'[A-ZÁÉÍÓÚ]{4}', p) and not re.match(r'^[“"]?[a-z\d]', p)):
            cur = None if not (cur and cur.startswith((disp_prefix, 'dc'))) else cur
            continue
        if cur is None:
            continue
        q = unquote(p)
        if ITEM.fullmatch(q.strip() + ' ') or re.fullmatch(r'[a-zñ]\)|\d+\)', q.strip()):
            continue                # a repealed item: only its label is left once the note is dropped
        out[cur]['lines'].append(q)
    # a heading run into its first paragraph ("Artículo 3.- A vivir en un ambiente sano.-El niño ...") is split after
    # the sumilla's closing ".-"
    for u in out.values():
        m = re.match(r'^((?:Art[íi]culo\s+\S+(?:\s+(?:del\s+)?T[íi]tulo\s+Preliminar)?|[A-ZÁÉÍÓÚ][a-záéíóú]+(?:\s+Disposici[óo]n'
                     r'\s+Complementaria)?)\s*\.\s*-\s*[^.]{1,160}?\.\s?-)\s*(\S.*)$', u['lines'][0])
        if m:
            u['lines'][0:1] = [m.group(1), m.group(2)]
    # a heading with nothing after it is an article Editora Perú prints as repealed (its note dropped)
    for k in [k for k, u in out.items() if re.fullmatch(r'Art[íi]culo\s+\S+\s*\.?-?', u['lines'][-1])]:
        del out[k]
    if ord_heads2:      # a disposition with nothing after its ordinal ("Segunda.-") is printed as repealed
        for k in [k for k, u in out.items() if len(u['lines']) == 1 and ORDH2.match(u['lines'][0])
                  and (ORDH2.fullmatch(u['lines'][0].strip() + ' ') or (len(u['lines'][0]) < 160
                       and not re.search(r'[.:;”]\s*$', u['lines'][0])))]:
            del out[k]     # ... or with only its epigraph ("Décimo Quinta.- Ejecución Coactiva")
    if caps_heads:
        # (opt-in) all-capital epigraphs keep the hyphen of a line-end word break ("PRO-CESAL"); it is removed where the
        # joined word occurs elsewhere in the file and the hyphenated one does not ("CONTENCIOSO-TRIBUTARIO" stays)
        vocab = set(w.lower() for q in ps for w in re.findall(r'[^\W\d_]+(?:-[^\W\d_]+)*', q))

        def dehyph(mt):
            a, b = mt.group(1), mt.group(2)
            return a + b if (a + b).lower() in vocab else mt.group(0)
        for k, u in out.items():
            if k.startswith('art-'):
                u['lines'][0] = re.sub(r'\b([A-ZÁÉÍÓÚÑ]+)- ?([A-ZÁÉÍÓÚÑ]+)\b', dehyph, u['lines'][0])
                if fn_markers:      # a footnote number right after the article's number ("Artículo 62-A.- (76) PLAZO")
                    u['lines'][0] = re.sub(r'^(Art[íi]culo\s+\S+)\s*\(\d{1,3}\)\s*', r'\1 ', u['lines'][0])
    for k in drop_units:      # (opt-in) provisions the file prints only as repealed, with their epigraph
        out.pop(k, None)
    return out


if __name__ == '__main__':
    us = units(sys.argv[1], sys.argv[2])
    keys = sys.argv[3:] or list(us)
    print(len(us), 'units')
    for k in keys:
        print(k, us[k]['label'])
        for l in us[k]['lines']:
            print('   |', l)
