"""Amendments to the Código Penal after the twelfth official edition (31 May 2016), replayed from each law's own
El Peruano text (penal/lawtext.py).

A law quotes the Code's new wording between “ and ”: a whole article, or an article with "(…)" / "[…]" standing for
wording left as it was. Which quoted article belongs to the Code is read from the law's own operative sentence
("Modifícanse los artículos 46, 108-B … del Código Penal"); quotes of other codes in the same law are left out.
Every word of a new version comes from the cached PDF; the program only decides where a quoted paragraph goes:

  whole article quoted          the article is replaced
  quote with ellipses           each quoted labelled paragraph ("2.", "d)", "a.") replaces the paragraph with the
                                same label, searched after the previous one; a label the article lacks is inserted
                                after the paragraph before it; the heading line is replaced only if it is quoted
  "Derógase el artículo N"      the article is removed

Laws whose wording cannot be placed this way carry hand operations in laws.json ("ops"), each naming the quoted
paragraphs it uses; the checkpoints (penal/compare.py against Editora Perú's NLA) test the result.
"""
from __future__ import annotations

import re

from base import HEAD as BHEAD
from edition import clean_par, label_of

ELL = re.compile(r'^[\(\[]\s*(?:…|\.\s*\.\s*\.|\.\.\.)\s*[\)\]]\s*[.;,]?$|^…$|^\.\.\.$')
QOPEN = ('“', '"', '«')
QCLOSE = ('”', '"', '»')
PROV = re.compile(r'^(?:Art[íi]culo\s+(?:\d+|[ÚU]nico|[IVX]+)\b|(?:PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]PTIMA|'
                  r'S[ÉE]TIMA|OCTAVA|NOVENA|D[ÉE]CIMA|[ÚU]NICA)\b|DISPOSICI[ÓO]N|DISPOSICIONES|POR TANTO|'
                  r'Primera\.|Segunda\.|Tercera\.|Cuarta\.|Quinta\.|Sexta\.|S[ée]ptima\.|S[ée]tima\.|Octava\.|'
                  r'Novena\.|D[ée]cima|[ÚU]nica\.)', re.I)
CP = re.compile(r'C[óo]digo\s+Penal', re.I)
OTHER = re.compile(r'(?:Procesal|Procedimientos|Ejecuci[óo]n|Responsabilidad)\s+Penal|Penal\s+Militar|'
                   r'C[óo]digo\s+(?:Civil|Tributario|de\s+los\s+Niños|Procesal|de\s+Ejecuci)|\bLey\s+(?:N[°º.]?\s*)?\d{4,5}|'
                   r'Decreto\s+(?:Legislativo|Ley|Supremo)\s+(?:N[°º.]?\s*)?\d+', re.I)
QHEAD = re.compile(r'^Art[íi]culo\s+(\d+|[IVX]+)\s*[°º]?\s*(?:-\s*([A-ZÑ])\b)?(?=\s*[.°º:-]|\s*$)')
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}


def art_key(num: str, suf: str | None) -> str:
    if num in ROMAN:
        return 'tp-%02d' % ROMAN[num]
    s = suf.lower() if suf else ''
    s = 'nn' if s == 'ñ' else s          # keys are ASCII; "129-Ñ" sorts between 129-N and 129-O
    return 'art-%03d%s' % (int(num), ('-' + s) if s else '')


def art_label(key: str) -> str:
    if key.startswith('tp-'):
        return 'Título Preliminar, art. %s' % [k for k, v in ROMAN.items() if v == int(key[3:])][0]
    m = re.fullmatch(r'art-(\d+)(?:-([a-z]+))?', key)
    s = {'nn': 'Ñ'}.get(m.group(2) or '', (m.group(2) or '').upper())
    return 'Art. %d%s' % (int(m.group(1)), '-' + s if s else '')


def strip_quotes(p: str) -> str:
    p = p.strip()
    p = re.sub(r'\s+POR TANTO:?$', '', p)       # the promulgation formula run into the last quoted line
    if p[:1] in QOPEN:
        p = p[1:]
    p = re.sub(r'[”"»]\s*([.;,]?)\s*$', r'\1', p)
    return p.strip()


def provisions(paras: list[str]) -> list[dict]:
    """The law's own provisions: heading, operative paragraphs (outside quotes) and quoted blocks."""
    out = []
    cur = None
    inq = False
    for p in paras:
        s = p.strip()
        if inq and (s.startswith('POR TANTO') or re.match(
                r'^(?:Art[íi]culo\s+\d+|PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]P?TIMA|OCTAVA|NOVENA|'
                r'D[ÉE]CIMA|[ÚU]NICA|Primera|Segunda|Tercera|Cuarta|Quinta|Sexta|S[ée]p?tima|Octava|Novena|D[ée]cima|'
                r'[ÚU]nica)\b[^a-z]{0,6}\s*(?:Modificaci|Incorporaci|Derogaci|Vigencia|Refrendo)', s)):
            inq = False          # an unclosed quote: the law's next provision ends it
        if not inq and s[:1] in QOPEN:
            inq = True
            cur['quotes'].append([]) if cur is not None else None
        if inq:
            if cur is not None:
                cur['quotes'][-1].append(s)
            closes = s.count('”') + s.count('»')
            opens = s.count('“') + s.count('«')
            if closes > opens - (1 if s[:1] in ('“', '«') else 0) or (s.endswith('"') and len(s) > 1) or \
                    re.search(r'[”"»]\s*[.;,]?\s*$', s):
                inq = False
            continue
        if PROV.match(s):
            # some laws print the new articles without quote marks: an "Artículo N" the operative sentence
            # announces for the Code is quoted text, not the law's own next article
            m = QHEAD.match(s)
            intro = ' '.join(cur['intro']) if cur is not None else ''
            if cur is not None and m and CP.search(intro) and (cur.get('unquoted') or (
                    not cur['quotes'] and intro.rstrip().endswith(':'))) and \
                    not LAW_PROV.match(s[m.end():].lstrip(' .-–')):
                nums = numbers_before_cp(intro)
                if nums and art_key(m.group(1), m.group(2)) in nums and \
                        art_key(m.group(1), m.group(2)) != _own_key(cur['head']):
                    cur['quotes'].append([s])
                    cur['unquoted'] = True
                    continue
            cur = {'head': s, 'intro': [s], 'quotes': []}
            out.append(cur)
            continue
        if cur is not None:
            if cur.get('unquoted'):
                cur['quotes'][-1].append(s)
            else:
                cur['intro'].append(s)
    return out


LAW_PROV = re.compile(r'(?:Modificaci[óo]n|Modifica|Incorporaci[óo]n|Incorpora|Derogaci[óo]n|Deroga|Objeto|Finalidad|'
                      r'Vigencia|Refrendo|Financiamiento|[ÁA]mbito|Sustituci[óo]n|Reglamenta|Definiciones|Creaci[óo]n|'
                      r'Adecuaci[óo]n|Aplicaci[óo]n|Implementaci[óo]n)\b', re.I)


def _own_key(head: str):
    m = QHEAD.match(head)
    return art_key(m.group(1), m.group(2)) if m else None


def split_articles(block: list[str]) -> list[tuple[str, list[str]]]:
    """A quoted block can hold several articles: [(key, paragraphs)] with the quote marks removed."""
    ps = [strip_quotes(p) for p in block]
    ps = [p for p in ps if p]
    out = []
    i = 0
    while i < len(ps):
        if QHEAD.match(ps[i]) or (i + 1 < len(ps) and QHEAD.match(ps[i + 1]) and not label_of(ps[i])
                                   and not ELL.match(ps[i]) and len(ps[i]) < 160
                                   and not re.search(r'[.;:,]$', ps[i])):       # a sumilla has no full stop
            j = i if QHEAD.match(ps[i]) else i + 1
            m = QHEAD.match(ps[j])
            out.append((art_key(m.group(1), m.group(2)), ps[i:j + 1]))
            i = j + 1
            continue
        if out:
            out[-1][1].append(ps[i])
        else:
            out.append((None, [ps[i]]))
        i += 1
    return out


def numbers_before_cp(intro: str) -> set[str] | None:
    """Article keys the operative sentence ties to the Código Penal, or None if it names none."""
    keys = set()
    for m in CP.finditer(intro):
        before = intro[max(0, m.start() - 400):m.start()]
        if re.search(r'(?:Procesal|Procedimientos|Ejecuci[óo]n|Responsabilidad)\s*$', before, re.I):
            continue
        a = list(re.finditer(r'art[íi]culos?\s', before, re.I))
        if not a:
            continue
        seg = before[a[-1].end():]
        if re.search(r'\b(?:Ley|Decreto|C[óo]digo)\b', seg):
            seg = re.split(r'\b(?:Ley|Decreto|C[óo]digo)\b', seg)[0]
        for n in re.finditer(r'\b(\d{1,3})(?:\s*[-–]\s*([A-ZÑ]))?\b', seg):
            keys.add(art_key(n.group(1), n.group(2)))
    return keys or None


def cp_quotes(paras: list[str], every: bool = False) -> tuple[list, list]:
    """([(key, paragraphs, provision head)], [notes]) for the quotes that belong to the Code. every=True returns
    every quoted article (for a law that amends the Code through another amending law, e.g. Ley 31673)."""
    res, notes = [], []
    for pr in provisions(paras):
        intro = ' '.join(pr['intro'])
        if every:
            for block in pr['quotes']:
                for key, ps in split_articles(block):
                    if key is not None:
                        res.append((key, ps, intro))
            continue
        if not CP.search(intro):
            continue
        cp_only = not any(not re.match(r'(?:Procesal|Procedimientos|Ejecuci|Responsabilidad)', m.group(0), re.I)
                          and True for m in OTHER.finditer(intro)) and not re.search(
            r'(?:Procesal|Procedimientos|Ejecuci[óo]n|Responsabilidad)\s+Penal', intro, re.I)
        nums = numbers_before_cp(intro)
        for block in pr['quotes']:
            for key, ps in split_articles(block):
                if key is None:
                    notes.append(f'{pr["head"][:60]}: quote without an article heading: {ps[0][:80]}')
                    continue
                if not cp_only and (nums is None or key not in nums):
                    continue          # the provision amends another norm too: only articles it ties to the Code
                if nums is not None and key not in nums:
                    notes.append(f'{pr["head"][:60]}: quoted {key} not named in the operative sentence')
                res.append((key, ps, ' '.join(pr['intro'])))
    return res, notes


def cp_repeals(paras: list[str]) -> tuple[list, list]:
    """Whole articles of the Code the law repeals, and repeals of parts (left to hand operations)."""
    whole, partial = [], []
    for pr in provisions(paras):
        intro = ' '.join(pr['intro'])
        for m in re.finditer(r'Der[óo]g(?:a|u)[^.]*?C[óo]digo\s+Penal', intro, re.I):
            s = m.group(0)
            if re.search(r'(?:Procesal|Procedimientos|Ejecuci[óo]n|Responsabilidad)\s+Penal\s*$', s, re.I):
                continue
            if re.search(r'numeral|inciso|literal|p[áa]rrafo', s, re.I):
                partial.append(s[:200])
                continue
            a = list(re.finditer(r'art[íi]culos?\s', s, re.I))
            if a:
                seg = re.split(r'\b(?:Ley|Decreto|C[óo]digo)\b', s[a[-1].end():])[0]
                for n in re.finditer(r'\b(\d{1,3})(?:\s*[-–]\s*([A-ZÑ]))?\b', seg):
                    if art_key(n.group(1), n.group(2)) not in whole:
                        whole.append(art_key(n.group(1), n.group(2)))
    return whole, partial


# ---------------------------------------------------------------- placing quoted wording

def _same_label(a, b):
    return a is not None and b is not None and a[1].lower() == b[1].lower() and \
        (a[0] == b[0] or {a[0], b[0]} <= {'lit', 'inc', 'num'} and not a[1].isdigit() == b[1].isdigit())


ORDINALS = {'primer': 1, 'primero': 1, 'segundo': 2, 'tercer': 3, 'tercero': 3, 'cuarto': 4, 'quinto': 5,
            'sexto': 6, 'séptimo': 7, 'sétimo': 7, 'octavo': 8, 'noveno': 9, 'décimo': 10}


def paragraph_hint(intro: str, key: str) -> dict | None:
    """What the operative sentence says about an unnumbered paragraph of the article: {'n': 1.. or 'last',
    'add': bool}. "Modifícase el cuarto párrafo del artículo 296-A" -> {'n': 4, 'add': False}."""
    num = key.split('-', 1)[1].lstrip('0').upper().replace('-NN', '-Ñ')
    for m in re.finditer(r'(?:(\w+)\s+)?p[áa]rrafos?(?:\s+(\w+))?\b([^.;]{0,60}?)art[íi]culo\s+' + re.escape(num)
                         + r'\b', intro, re.I):
        if re.search(r'n[uú]mer|literal|inciso', m.group(3), re.I):
            continue                     # "el párrafo 3 del numeral 2": not an article paragraph
        before = intro[max(0, m.start() - 120):m.start()]
        verbs = re.findall(r'(modif\w*|incorp\w*|sustitu\w*|agr[eé]g\w*|adici\w*)', before, re.I)
        if not verbs:
            continue
        last_verb = list(re.finditer(r'(modif\w*|incorp\w*|sustitu\w*|agr[eé]g\w*|adici\w*)', before, re.I))[-1]
        if re.search(r'n[uú]meral|literal|inciso', before[last_verb.start():], re.I):
            continue                     # "incorpórase los numerales 4, 5 y 6 al segundo párrafo": items, not a paragraph
        w1, w2 = (m.group(1) or '').lower(), (m.group(2) or '').lower()
        n = None
        for w in (w1, w2):
            if w in ('último', 'ultimo'):
                n = 'last'
            elif w in ORDINALS:
                n = ORDINALS[w]
        return {'n': n, 'add': verbs[-1].lower().startswith(('incorp', 'agr', 'adic'))}
    # "Se modifica el artículo 22 —incorporando un párrafo tercero— del Código Penal"
    for m in re.finditer(r'art[íi]culo\s+' + re.escape(num) + r'\b([^.;]{0,40}?)(?:(\w+)\s+)?p[áa]rrafos?(?:\s+(\w+))?',
                         intro, re.I):
        if re.search(r'n[uú]mer|literal|inciso', m.group(1), re.I):
            continue
        around = intro[max(0, m.start() - 80):m.end()]
        verbs = re.findall(r'(modif\w*|incorp\w*|sustitu\w*|agr[eé]g\w*|adici\w*)', around, re.I)
        if not verbs:
            continue
        n = None
        for w in ((m.group(2) or '').lower(), (m.group(3) or '').lower()):
            if w in ('último', 'ultimo'):
                n = 'last'
            elif w in ORDINALS:
                n = ORDINALS[w]
        return {'n': n, 'add': verbs[-1].lower().startswith(('incorp', 'agr', 'adic'))}
    return None


def merge(cur: list[str], q: list[str], hint: dict | None = None) -> tuple[list[str], list[str]]:
    """Apply a quote with ellipses to the current paragraphs. Returns (new paragraphs, warnings)."""
    warn = []
    runs: list[list[str]] = [[]]
    for p in q:
        if ELL.match(p):
            runs.append([])
        else:
            runs[-1].append(p)
    out = list(cur)
    adding = False
    # run 0: the heading (and whatever follows it before the first ellipsis)
    head = runs[0]
    hi = next((i for i, p in enumerate(out) if BHEAD.match(p)), 0)
    pos = hi + 1
    if head:
        hq = next((i for i, p in enumerate(head) if QHEAD.match(p)), None)
        if hq is not None:
            pre, hline, rest = head[:hq], head[hq], head[hq + 1:]
            if pre:                                       # a sumilla line before the heading
                if hi > 0:
                    out[hi - 1:hi] = pre
                    hi = hi - 1 + len(pre)
                else:
                    out[0:0] = pre
                    hi += len(pre)
            old = out[hi]
            mo = BHEAD.match(old)
            old_rest = old[mo.end():].strip() if mo else ''
            old_has_body = has_body(old_rest)
            mq = QHEAD.match(hline)
            q_sumilla = mq and len(re.sub(r'^[\s.°º-]+', '', hline[mq.end():]).strip()) > 0 and \
                not re.search(r'[.:;]$', hline.strip())
            if q_sumilla and not pre and hi > 0 and label_of(out[hi - 1]) is None and not BHEAD.match(out[hi - 1]):
                del out[hi - 1]                  # the sumilla now sits in the quoted heading line
                hi -= 1
            out[hi] = hline
            pos = hi + 1
            if old_has_body and rest and label_of(rest[0]) is None:
                out.insert(pos, rest[0])         # the old heading line carried the first sentence
                pos += 1
                rest = rest[1:]
            elif old_has_body and hline.strip() != old.strip():
                out.insert(pos, old_rest)        # the first sentence stays as it was, now under the new heading
                pos += 1
                warn.append('kept the first sentence of the old heading line')
            runs[0] = rest
        else:
            warn.append('first run has no heading: ' + head[0][:60])
            runs[0] = []
    first_pos = pos
    for ri, run in enumerate(runs):
        for p in run:
            lab = label_of(p)
            if lab is None:
                # an unlabelled paragraph: right after the heading it replaces the paragraph there; later, the
                # next unlabelled one
                if ri == 0 and pos == first_pos and pos < len(out) and label_of(out[pos]) is None:
                    out[pos] = p
                    pos += 1
                    continue
                if hint and ri >= 1:
                    # the operative sentence names the paragraph ("el cuarto párrafo", "un último párrafo")
                    # the article's paragraphs, not counting a sentence that continues a numbered item (an
                    # unlabelled paragraph between two labelled ones)
                    lab_at = [label_of(out[k]) is not None for k in range(len(out))]
                    body = [k for k in range(hi + 1, len(out)) if not lab_at[k] and not (
                        k > 0 and lab_at[k - 1] and any(lab_at[k + 1:]) and
                        next(x for x in lab_at[k + 1:] if True) is not None and
                        k + 1 < len(out) and lab_at[k + 1])]
                    n = hint['n']
                    if hint['add']:
                        if isinstance(n, int) and n - 1 < len(body):
                            j = body[n - 1]
                        else:
                            j = len(out)
                        out.insert(j, p)
                        warn.append('paragraph added at %s (%s)' % (j, n))
                    else:
                        j = body[-1] if n == 'last' else (body[n - 1] if isinstance(n, int) and n - 1 < len(body)
                                                           else None)
                        # a source that ran two paragraphs together shifts the count: when the named paragraph
                        # reads nothing like the new wording and another one does, take that one
                        alt = max(body, key=lambda k: _alike(out[k], p)) if body else None
                        if alt is not None and (j is None or _alike(out[j], p) < 0.5) and _alike(out[alt], p) >= 0.65:
                            warn.append('paragraph hint %s: took the alike paragraph %d instead of %s' % (n, alt, j))
                            j = alt
                        if j is None:
                            raise SystemExit('paragraph hint %s does not fit: %s' % (hint, p[:60]))
                        warn.append('paragraph %s replaced: %s -> %s' % (n, out[j][:40], p[:40]))
                        out[j] = p
                    pos = j + 1
                    adding = hint['add']
                    hint = None
                    continue
                if adding:
                    out.insert(pos, p)           # further added paragraphs follow the first
                    pos += 1
                    continue
                # otherwise the unlabelled paragraph from here on that reads most like it (the wording a law
                # amends stays largely the same); none alike: a new paragraph, placed here
                cands = [k for k in range(pos, len(out)) if label_of(out[k]) is None]
                best, j = 0.0, None
                for k in cands:
                    r = _alike(out[k], p)
                    if r > best:
                        best, j = r, k
                if j is None or best < 0.65:
                    out.insert(pos, p)
                    warn.append('unlabelled inserted (best %.2f): %s' % (best, p[:50]))
                    pos += 1
                else:
                    if out[j] != p:
                        warn.append('unlabelled replaced (%.2f): %s -> %s' % (best, out[j][:40], p[:40]))
                    out[j] = p
                    pos = j + 1
                continue
            adding = False
            j = next((k for k in range(pos, len(out)) if _same_label(label_of(out[k]), lab)), None)
            if j is not None:
                out[j] = p
                pos = j + 1
                continue
            # a new label: right after the label before it ("i)" after "h)", "7." after "6."), with that label's
            # sub-items; failing that, after the last label of its kind
            j = None
            pl = _pred(lab)
            if pl is not None:
                jp = next((k for k in range(max(pos - 1, 0), len(out)) if _same_label(label_of(out[k]), pl)), None)
                if jp is not None:
                    k = jp + 1
                    # a numeral carries its literals with it; a literal has no sub-items
                    while _kind(lab) == 'num' and k < len(out) and label_of(out[k]) is not None and \
                            _kind(label_of(out[k])) == 'lit':
                        k += 1
                    out.insert(k, p)
                    warn.append('inserted %s after %s at %d' % (lab, pl, k))
                    pos = k + 1
                    continue
            for k in range(len(out) - 1, pos - 2, -1):
                lk = label_of(out[k]) if k >= 0 else None
                if lk is not None and lk[0] == lab[0] or (lk is not None and _kind(lk) == _kind(lab)):
                    j = k
                    break
            if j is None:
                j = pos - 1
            k = j + 1
            while k < len(out) and label_of(out[k]) is None and _kind(lab) != 'num':
                break
            out.insert(k, p)
            warn.append('inserted %s at %d' % (lab, k))
            pos = k + 1
    return out, warn


def _pred(lab):
    """The label before this one: ('lit', 'i') -> ('lit', 'h'); ('num', '7') -> ('num', '6'); ('num', '317.3') ->
    ('num', '317.2'); None for a first label."""
    kind, v = lab
    if re.fullmatch(r'\d+', v):
        return (kind, str(int(v) - 1)) if int(v) > 1 else None
    m = re.fullmatch(r'(.*\.)(\d+)', v)
    if m:
        return (kind, m.group(1) + str(int(m.group(2)) - 1)) if int(m.group(2)) > 1 else None
    letters = 'abcdefghijklmnñopqrstuvwxyz'
    if len(v) == 1 and v.lower() in letters and v.lower() != 'a':
        return (kind, letters[letters.index(v.lower()) - 1])
    return None


def has_body(rest: str) -> bool:
    """Whether what follows "Artículo N.-" on a heading line is the article's first sentence rather than its sumilla
    ("Conversión de la pena ... personal." is a sumilla with a full stop)."""
    rest = (rest or '').strip()
    if not rest:
        return False
    return len(rest) > 140 or bool(re.search(r'[:;]$', rest)) or (rest.endswith('.') and len(rest.split()) > 16)


def _alike(a: str, b: str) -> float:
    import difflib
    wa, wb = re.findall(r'\w+', a.lower()), re.findall(r'\w+', b.lower())
    if not wa or not wb:
        return 0.0
    sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
    same = sum(bl.size for bl in sm.get_matching_blocks())
    # an amended paragraph keeps most of its old words, even when the law lengthens it
    return max(sm.ratio(), same / min(len(wa), len(wb)) if min(len(wa), len(wb)) >= 8 else 0.0)


def _kind(lab):
    if lab is None:
        return None
    if lab[1].isdigit() or re.fullmatch(r'\d+(?:\.\d+)*', lab[1]):
        return 'num'
    return 'lit'
