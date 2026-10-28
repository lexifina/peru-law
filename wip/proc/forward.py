"""Amendments after the eighth edition (17 Nov 2024), replayed from the laws' own texts.

The texts are Congreso's ADLP transcriptions ("PUBLICADA EL … EN EL DIARIO OFICIAL EL PERUANO"), which have a text
layer. Each law quotes the new wording between “ and ”; "[…]" marks wording left as it was. The operations below
only say WHERE each quoted paragraph goes; every word comes from the cached PDF.
"""
from __future__ import annotations

import hashlib
import re

import fitz

import fetch
from edition import clean_par, label_of

ADLP = 'https://www.leyes.congreso.gob.pe/Documentos/2021_2026/ADLP/Texto_Consolidado/%s-TXM.pdf'
ELLIPSIS = re.compile(r'^\[\s*(?:…|\.\.\.)\s*\]\.?$')
ART = re.compile(r'^Art[íi]culo\s+([IVXL]+|\d+(?:-[A-Z])?)\s*\.(?:-)?\s')

# law, published, in force (Constitución art. 109: none of these laws has its own vigencia clause), operations
LAWS = [
    ('32181', '2024-12-11', '2024-12-12', [
        ('art-255', 'para', '255', ('num', '1')),
        ('art-261', 'para', '261', ('num', '1')),
        ('art-261', 'drop', None, ('lit', 'a')),          # Única Disposición Complementaria Derogatoria
        ('art-292-a', 'whole', '292-A', None),
        ('art-261-a', 'whole', '261-A', None),
        ('art-268-b', 'whole', '268-B', None),
    ]),
    ('32182', '2024-12-11', '2024-12-12', [
        ('art-268', 'para', '268', ('lit', 'c')),
    ]),
    ('32255', '2025-03-10', '2025-03-11', [
        ('art-261', 'para', '261', ('num', '1')),
        ('art-261', 'insert_before', '261', ('lit', 'a'), ('lit', 'b')),
        ('art-261', 'para', '261', ('lit', 'b')),
        ('art-261', 'para', '261', ('lit', 'c')),
    ]),
    ('32374', '2025-06-07', '2025-06-08', [
        ('tp-09', 'append', 'IX', ('num', '4')),
        ('art-086', 'para', '86', ('num', '1')),
        ('art-086', 'para', '86', ('num', '2')),
        ('art-088', 'para', '88', ('num', '7')),
        ('art-337', 'para', '337', ('lit', 'a')),
    ]),
]


def law_text(n: str):
    path = fetch.cached(ADLP % n)
    if path is None:
        raise SystemExit(f'not in the cache: {ADLP % n}')
    doc = fitz.open(str(path))
    lines = [l.rstrip() for p in doc for l in p.get_text().split('\n')]
    return path, [l for l in lines if l.strip()]


def title_of(lines) -> str:
    i = next(i for i, l in enumerate(lines) if l.strip().startswith('LEY QUE') or l.strip().startswith('LEY DE'))
    out = []
    while i < len(lines) and not lines[i].strip().startswith('LEY ' + '3'):
        out.append(lines[i].strip())
        i += 1
    t = ' '.join(out)
    return t[0] + t[1:].lower() if t else ''


def quoted_articles(lines) -> dict[str, list[str]]:
    """Article number -> quoted paragraphs ('[…]' kept as a marker) for the Code's articles (the other codes the
    same law amends are kept too; callers pick by number and code)."""
    text = '\n'.join(l.strip() for l in lines)
    out: dict[str, list[list[str]]] = {}
    for m in re.finditer(r'“(.*?)”', text, re.S):
        block = m.group(1).split('\n')
        cur = None
        for l in block:
            l = l.strip()
            if not l:
                continue
            a = ART.match(l)
            if a:
                cur = a.group(1)
                out.setdefault(cur, []).append([l])
                continue
            if cur is None:
                continue
            paras = out[cur][-1]
            if ELLIPSIS.match(l) or label_of(l) or ELLIPSIS.match(paras[-1]):
                paras.append(l)
            else:
                paras[-1] = paras[-1] + ' ' + l
    return {k: [clean_par(re.sub(r'[”"]\.?$', '', p).strip()) for p in v[-1]] for k, v in out.items()}


def find(paras, lab, after=0):
    for i in range(after, len(paras)):
        if i and label_of(paras[i]) == lab:
            return i
    return None


def apply(units: dict, labels: dict) -> list[tuple]:
    """Replays LAWS on units (key -> paragraphs). Returns [(law, published, in force, sha256, url, title,
    {key: paragraphs or None})]."""
    out = []
    for n, pub, day, ops in LAWS:
        path, lines = law_text(n)
        q = quoted_articles(lines)
        changed = {}
        for op in ops:
            key, kind, art = op[0], op[1], op[2]
            cur = list(changed.get(key) or units.get(key) or [])
            if kind == 'whole':
                new = [p for p in q[art] if not ELLIPSIS.match(p)]
                if len(new) != len(q[art]):
                    raise SystemExit(f'Ley {n}: art. {art} quoted with […] but used whole')
                changed[key] = new
                continue
            src = q[art] if art else []
            if kind == 'drop':
                i = find(cur, op[3])
                del cur[i]
            elif kind == 'append':
                i = find(src, op[3])
                cur.append(src[i])
            elif kind == 'insert_before':
                i = find(src, op[3])
                j = find(cur, op[4])
                cur.insert(j, src[i])
            elif kind == 'para':
                lab = op[3]
                i = find(src, lab)
                if lab[0] == 'lit':        # inside its numeral when the quote names one
                    num = next((p for p in src[:i] if label_of(p) and label_of(p)[0] == 'num'), None)
                    start = find(cur, label_of(num)) if num else 0
                    j = find(cur, lab, start or 0)
                else:
                    j = find(cur, lab)
                if i is None or j is None:
                    raise SystemExit(f'Ley {n}: {key} {lab} not found')
                if label_of(cur[j + 1]) is None if j + 1 < len(cur) else False:
                    raise SystemExit(f'Ley {n}: {key} {lab} is followed by unlabelled paragraphs; check the splice')
                cur[j] = src[i]
            changed[key] = cur
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        out.append((n, pub, day, sha, ADLP % n, title_of(lines), changed))
        for k, v in changed.items():
            units[k] = v
    return out
