"""Word-level comparison of a rebuilt state of the Código Penal with an Editora Perú NLA capture (penal/nla.py).

Each unit is compared without its heading ("Artículo 108-B.-"): its sumilla with the end of the previous NLA segment,
its body with the start of its own segment. Words only: punctuation, case, quotes, "N°" and degree signs are ignored.

    compare(units, segs) -> [(key, what, detail)]      what: body | sumilla | missing | extra
"""
from __future__ import annotations

import difflib
import re

from nla import words

HEAD = re.compile(r'^(?:Art[íi]culo\s+([IVXL]+|\d+)\s*[°º]?\s*(?:-\s*([A-ZÑ])\b)?\s*[°º]?\s*\.?\s*-?|'
                  r'(?:PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|Primera|Segunda|Tercera|Cuarta|Quinta)\s*\.\s*-)\s*')


def split_unit(text: str) -> tuple[str, str]:
    """(sumilla, body) of a unit's text, the heading words dropped."""
    ls = [l for l in text.split('\n') if l.strip()]
    if not ls:
        return '', ''
    sumilla = ''
    if not HEAD.match(ls[0]) and len(ls) > 1 and HEAD.match(ls[1]):
        sumilla, ls = ls[0], ls[1:]
    m = HEAD.match(ls[0])
    first = ls[0][m.end():] if m else ls[0]
    if m and not sumilla and len(ls) > 1 and first and len(first) < 140 and not re.search(r'[.:;]$', first.strip()):
        sumilla, first = first, ''      # "Artículo 108-B. Feminicidio" on a line of its own
    return sumilla, ' '.join([first] + ls[1:])


def _show(a, b, n=12):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != 'equal':
            out.append('%s ours[%s] nla[%s]' % (op, ' '.join(a[i1:i2][:n]), ' '.join(b[j1:j2][:n])))
    return '; '.join(out[:4])


def compare(units: dict, segs: list, skip_tail: int = 60) -> list:
    res = []
    order = [k for k, _, _ in segs]
    seen = set()
    nla_text = {}
    for i, (k, t, _) in enumerate(segs):
        if k in seen:
            continue
        seen.add(k)
        nla_text[k] = (i, t)
    for k in units:
        if k not in nla_text and 'DEROGAD' not in units[k]['text'].upper():
            res.append((k, 'extra', units[k]['text'][:100]))
    for k in order:
        if k not in units:
            i, t = nla_text[k]
            w = words(t)
            if len(w) > 25:
                res.append((k, 'missing', ' '.join(w[:20])))
    for k, (i, t) in nla_text.items():
        if k not in units:
            continue
        sumilla, body = split_unit(units[k]['text'])
        ob = words(body)
        tb = words(t)
        if tb[:len(ob)] != ob:
            # the NLA may leave a repealed article with no body
            res.append((k, 'body', _show(ob, tb[:len(ob) + 10])))
        if sumilla:
            os_ = words(sumilla)
            prev = words(segs[i - 1][1]) if i else []
            if prev[-len(os_):] != os_:
                res.append((k, 'sumilla', '%s | nla tail: %s' % (' '.join(os_), ' '.join(prev[-len(os_) - 3:]))))
    return res
