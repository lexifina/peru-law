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
QHEAD = re.compile(r'^Art[íi]culo\s+(\d+|[IVX]+)\s*[°º]?\s*(?:-\s*([A-Z])\b)?(?=\s*[.°º-])')
ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}


def art_key(num: str, suf: str | None) -> str:
    if num in ROMAN:
        return 'tp-%02d' % ROMAN[num]
    return 'art-%03d%s' % (int(num), ('-' + suf.lower()) if suf else '')


def art_label(key: str) -> str:
    if key.startswith('tp-'):
        return 'Título Preliminar, art. %s' % [k for k, v in ROMAN.items() if v == int(key[3:])][0]
    m = re.fullmatch(r'art-(\d+)(?:-([a-z]))?', key)
    return 'Art. %d%s' % (int(m.group(1)), '-' + m.group(2).upper() if m.group(2) else '')


def strip_quotes(p: str) -> str:
    p = p.strip()
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
            cur = {'head': s, 'intro': [s], 'quotes': []}
            out.append(cur)
            continue
        if cur is not None:
            cur['intro'].append(s)
    return out


def split_articles(block: list[str]) -> list[tuple[str, list[str]]]:
    """A quoted block can hold several articles: [(key, paragraphs)] with the quote marks removed."""
    ps = [strip_quotes(p) for p in block]
    ps = [p for p in ps if p]
    out = []
    i = 0
    while i < len(ps):
        if QHEAD.match(ps[i]) or (i + 1 < len(ps) and QHEAD.match(ps[i + 1]) and not label_of(ps[i])
                                   and not ELL.match(ps[i]) and len(ps[i]) < 160):
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
    for m in re.finditer(r'art[íi]culos?\s+((?:\d+(?:\s*-\s*[A-Z])?\s*(?:,|y|e)?\s*)+)(?:[^.]{0,80}?)\s*(?:del|al)\s+'
                         r'(?:presente\s+)?C[óo]digo\s+Penal', intro, re.I):
        for n in re.finditer(r'(\d+)(?:\s*-\s*([A-Z]))?', m.group(1)):
            keys.add(art_key(n.group(1), n.group(2)))
    return keys or None


def cp_quotes(paras: list[str]) -> tuple[list, list]:
    """([(key, paragraphs, provision head)], [notes]) for the quotes that belong to the Code."""
    res, notes = [], []
    for pr in provisions(paras):
        intro = ' '.join(pr['intro'])
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
                if nums is not None and key not in nums:
                    if cp_only:
                        notes.append(f'{pr["head"][:60]}: quoted {key} not named in the operative sentence')
                    else:
                        continue
                res.append((key, ps, pr['head']))
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
            for a in re.finditer(r'art[íi]culos?\s+((?:\d+(?:\s*-\s*[A-Z])?\s*(?:,|y|e)?\s*)+)', s, re.I):
                for n in re.finditer(r'(\d+)(?:\s*-\s*([A-Z]))?', a.group(1)):
                    whole.append(art_key(n.group(1), n.group(2)))
    return whole, partial


# ---------------------------------------------------------------- placing quoted wording

def _same_label(a, b):
    return a is not None and b is not None and a[1].lower() == b[1].lower() and \
        (a[0] == b[0] or {a[0], b[0]} <= {'lit', 'inc', 'num'} and not a[1].isdigit() == b[1].isdigit())


def merge(cur: list[str], q: list[str]) -> tuple[list[str], list[str]]:
    """Apply a quote with ellipses to the current paragraphs. Returns (new paragraphs, warnings)."""
    warn = []
    runs: list[list[str]] = [[]]
    for p in q:
        if ELL.match(p):
            runs.append([])
        else:
            runs[-1].append(p)
    out = list(cur)
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
            out[hi] = hline
            pos = hi + 1
            for p in rest:
                if pos < len(out) and label_of(out[pos]) is None and label_of(p) is None:
                    out[pos] = p
                else:
                    out.insert(pos, p)
                    warn.append('inserted after heading: ' + p[:50])
                pos += 1
        else:
            warn.append('first run has no heading: ' + head[0][:60])
    for run in runs[1:]:
        for p in run:
            lab = label_of(p)
            if lab is None:
                # an unlabelled paragraph: replace the next unlabelled one
                j = next((k for k in range(pos, len(out)) if label_of(out[k]) is None), None)
                if j is None:
                    out.insert(pos, p)
                    warn.append('unlabelled appended: ' + p[:50])
                    pos += 1
                else:
                    warn.append('unlabelled replaced: ' + out[j][:40] + ' -> ' + p[:40])
                    out[j] = p
                    pos = j + 1
                continue
            j = next((k for k in range(pos, len(out)) if _same_label(label_of(out[k]), lab)), None)
            if j is not None:
                out[j] = p
                pos = j + 1
                continue
            # a new label: after the block of the label before it
            j = None
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


def _kind(lab):
    if lab is None:
        return None
    if lab[1].isdigit() or re.fullmatch(r'\d+(?:\.\d+)*', lab[1]):
        return 'num'
    return 'lit'
