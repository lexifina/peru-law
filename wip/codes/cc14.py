"""Read the MINJUS 14th official edition of the Código Civil (gob.pe, current to 1 Aug 2014).

Body Cambria 9.5 pt, footnote calls 6.6 pt superscripts, footnotes Cambria 7 pt. Line reading and the
body/note split come from ../proc/edition.py (gitlaw-PE-proc), with a profile for this edition.

    read() -> (units, struct, notes)
      units:  OrderedDict key -> {'sumilla': str|None, 'paras': [str], 'calls': set(note numbers)}
      notes:  {n: {'header': str, 'quote': [paragraphs] | None, 'quote_kind': str|None}}
Only the cache is read.
"""
from __future__ import annotations

import re
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "proc"))
sys.path.insert(0, str(HERE.parent))
import edition  # noqa: E402
import fetch  # noqa: E402
import fitz  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)

URL = "https://cdn.www.gob.pe/uploads/document/file/5700008/5060551-codigo-civil-minjus-bcp_n-3.pdf?v=1705608699"
edition.PROFILES["cc14"] = {"body_min": 9.0, "furniture": ("Tahoma",), "top": 40, "bottom": 0}
MARK = edition.MARK
CALLS = re.compile(MARK + r"([^" + MARK + r"]*)" + MARK)
HEAD = re.compile(r"^“?Art[íi]culo\s+(\d+|[IVX]+)\s*\.?\s*[°º˚]?\s*(?:-\s*([A-Z])\b)?\s*[°º˚]?\s*(?:\.?\s*-|\.(?=\s))")
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}
STRUCT = re.compile(r"^(LIBRO|SECCI[ÓO]N|T[ÍI]TULO|CAP[ÍI]TULO|SUBCAP[ÍI]TULO|DISPOSICIONES)\b")


def key_of(head: str) -> str:
    m = HEAD.match(head)
    base, suf = m.group(1), m.group(2)
    if base in ROMAN:
        return "tp-%02d" % ROMAN[base]
    return "art-%04d%s" % (int(base), ("-" + suf.lower()) if suf else "")


def first_body_page(doc) -> int:
    for i in range(40, 80):
        t = doc[i].get_text()
        if "TÍTULO PRELIMINAR" in t and "Abrogación de la ley" in t:
            return i
    raise SystemExit("no body start")


def read():
    doc = fitz.open(fetch.cached(URL))
    first = first_body_page(doc)
    ls = edition.lines(doc, first, doc.page_count - 1, "cc14")
    # side tabs ("LIBRO I / DERECHO DE LAS PERSONAS") sit at the right edge in note type: drop them
    ls = [l for l in ls if not (l.kind == "note" and l.x > 370)]
    body, notes_l = split_notes(ls)
    # body ends after art. 2122
    units: "OrderedDict[str, dict]" = OrderedDict()
    struct: list[str] = []
    cur = None
    pend_sumilla: list = []
    started = False
    done = False
    groups: list = []   # (key, [lines])
    for l in body:
        t = l.text.strip()
        tc = CALLS.sub("", t).strip()
        if not started:
            if l.bold and tc.startswith("TÍTULO PRELIMINAR"):
                started = True
            else:
                continue
        if done:
            break
        if l.bold and HEAD.match(tc):
            k = key_of(tc)
            cur = {"key": k, "lines": [l], "sumilla": pend_sumilla}
            groups.append(cur)
            pend_sumilla = []
            continue
        if l.bold and l.x > 90:
            struct.append(tc)
            cur = None
            pend_sumilla = []
            continue
        if l.bold:
            # sumilla (one or two bold lines before an article head)
            pend_sumilla.append(l)
            cur = None
            continue
        if cur is not None:
            cur["lines"].append(l)
    for g in groups:
        paras = edition.paragraphs(g["lines"], 15.0)
        sumilla = " ".join(CALLS.sub("", x.text).strip() for x in g["sumilla"]) or None
        calls = set()
        for p in paras:
            calls |= {c for c in CALLS.findall(p)}
        for x in g["sumilla"]:
            calls |= set(CALLS.findall(x.text))
        if g["key"] in units:
            continue
        units[g["key"]] = {"sumilla": sumilla, "paras": paras, "calls": calls}
        if g["key"] == "art-2122":
            break
    notes = {}
    for n, nl in notes_l.items():
        notes[n] = parse_note(nl)
    return units, struct, notes


def split_notes(ls):
    """Like edition.split_notes, but the numbering of this edition does not start at 1 in the body."""
    body = [l for l in ls if l.kind == "body"]
    notes: dict = {}
    cur = None
    expect = None
    for l in ls:
        if l.kind != "note":
            continue
        m = edition.NOTE_START.match(l.text.strip())
        if m and l.x < 70 and (expect is None or int(m.group(1)) in (expect, expect + 1)):
            cur = int(m.group(1))
            expect = cur + 1
            rest = l.text.strip()[len(m.group(1)):].lstrip()
            notes[cur] = []
            if rest:
                notes[cur].append(edition.Line(l.page, l.y, l.x + 20, "note", rest, False, l.size, l.spans, l.x1))
            continue
        if cur is not None:
            notes[cur].append(l)
    return body, notes


TA = re.compile(r"^\s*(Texto|Denominación)\s+(anterior|original)[^:]*:\s*$", re.I)


def parse_note(nl) -> dict:
    head, quote, kind = [], None, None
    for l in nl:
        t = l.text.strip()
        if quote is None and TA.match(t):
            quote, kind = [], t
            continue
        (head if quote is None else quote).append(l)
    header = edition.clean_par(" ".join(x.text.strip() for x in head))
    q = None
    if quote is not None:
        q = edition.paragraphs(quote, 8.5)
    return {"header": header, "quote": q, "quote_kind": kind}

# the edition writes numerals as "3.-"; let edition.paragraphs see them as item labels
edition.LABEL = re.compile(r"^(?:(\d{1,3})\s*\.-?(?=\s|$)|(\d{1,3})\s*\)|([a-zñ])\s*\)|([a-zñ])\s*\.(?=\s)|([IVX]+)\s*\.(?=\s))")


def text14(u: dict) -> list[str] | None:
    """A 14th-edition unit as lines in the corpus layout: the sumilla line (if printed apart), then the
    paragraphs; footnote calls, degree marks after numbers and "DEROGADO." numerals removed. None if the
    whole article is printed as repealed."""
    lines = []
    if u["sumilla"]:
        lines.append(u["sumilla"].strip())
    for p in u["paras"]:
        p = CALLS.sub("", p).strip()
        p = re.sub(r"(\d)\s*\.?\s*[º°˚]", r"\1", p)
        p = p.replace("“", '"').replace("”", '"')
        if re.fullmatch(r"\d+\s*\.-?\s*DEROGAD[OA]S?\.?|[a-z]\)\s*DEROGAD[OA]\.?", p):
            continue
        lines.append(p)
    body = [x for x in lines if not (u["sumilla"] and x == u["sumilla"].strip())]
    if not body or re.fullmatch(r"Artículos?\s+[\d\s,y-]+\.?-?\s*(DEROGAD[OA]S?\.?)?", body[0]) and len(body) == 1:
        return None
    return lines
