"""Parse the Congreso de la República editions of the 1993 Constitution (text PDFs) into units.

"modern" editions (Congreso, May 2021 and Dec 2024; same typesetting) are read with PyMuPDF so that
font size and style separate the body (10 pt regular) from notes:
  * 2021: numbered footnotes in 7 pt at the page foot, superscript markers in the body;
  * 2024: inline notes after the annotated paragraph: a bold 8 pt header "(*) ... modificado por
    ... Ley Nº 31988 ..." and the future text in 10 pt italics; a bold "(*)" marker in the body.
Page footers (7 pt, y > 425) are dropped. Paragraphs come from vertical gaps between lines.

Everything here reads the cache only.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import fitz  # PyMuPDF

import fetch

ORD = {
    "primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4, "quinta": 5, "sexta": 6, "séptima": 7,
    "sétima": 7, "setima": 7, "octava": 8, "novena": 9, "décima": 10, "decima": 10,
    "decimoprimera": 11, "undécima": 11, "decimosegunda": 12, "duodécima": 12,
    "decimotercera": 13, "decimocuarta": 14, "decimoquinta": 15, "decimosexta": 16,
}
ORD_RE = "|".join(sorted(ORD, key=len, reverse=True))
ART = re.compile(r"^Artículo (\d+)\s*(?:°|º)?\s*(?:-\s*([A-Z]))?\s*(?:°|º)?\s*(?:\.\s*-|\.|-)?\s*")
DISP = re.compile(r"^(" + ORD_RE + r")\s*\.\s*-?\s*", re.I)
ITEM = re.compile(r"^(\d{1,2}|[a-z])\s*[.)]\s")
TAB = chr(9)
MARK = re.compile(r"⟦([^⟧]*)⟧")
FOOTER = re.compile(r"^\s*(CONSTITUCIÓN POLÍTICA DEL PERÚ\s*\d+|\d+\s*Edición del Congreso de la República)\s*$")


def clean(s: str) -> str:
    """Normalise publisher typesetting once: NBSP, tabs, quotes, dashes, spaces."""
    s = s.replace("\u00a0", " ").replace("\u00ad", "").replace("\t", " ")
    s = s.replace("‟", "“").replace("«", "“").replace("»", "”")
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("–", "-").replace("−", "-")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r" ([,;:.])", r"\1", s)
    return s.strip()


def split_head(t: str, end: int) -> str:
    """Drop the first `end` characters of the unmarked text of t (a heading such as "Artículo 7-A."),
    keeping any note markers that sit inside or right after it."""
    out_marks, i, plain = [], 0, 0
    while i < len(t) and plain < end:
        m = MARK.match(t, i)
        if m:
            out_marks.append(m.group(0))
            i = m.end()
            continue
        i += 1
        plain += 1
    while True:
        m = re.compile(r"\s*(⟦[^⟧]*⟧)").match(t, i)
        if not m:
            break
        out_marks.append(m.group(1))
        i = m.end()
    return "".join(out_marks) + t[i:].lstrip()


def unit_key(num: str, suf: str | None) -> str:
    return f"art-{int(num):03d}" + (f"-{suf.lower()}" if suf else "")


def unit_label(num: str, suf: str | None) -> str:
    return f"Artículo {int(num)}" + (f"-{suf}" if suf else "")


def ends_sentence(s: str) -> bool:
    s = MARK.sub("", s).rstrip()
    return bool(re.search(r"[.:;”\"]$", s))


@dataclass
class Row:
    page: int
    x: float
    y: float
    text: str
    size: float
    bold: bool
    italic: bool
    first_bold: str = ""  # text of a leading bold span


def rows_of(url: str) -> list[Row]:
    doc = fitz.open(str(fetch.cached(url)))
    out: list[Row] = []
    for pno, page in enumerate(doc):
        lines = []
        for b in page.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                spans = [s for s in l["spans"] if s["text"]]
                if spans:
                    lines.append((round(l["bbox"][1], 1), l["bbox"][0], spans))
        lines.sort(key=lambda t: (t[0], t[1]))
        merged: list[list] = []
        for y, x, spans in lines:
            if merged and abs(merged[-1][0] - y) < 2.5:
                merged[-1][2].extend(spans)
            else:
                merged.append([y, x, list(spans)])
        for y, x, spans in merged:
            spans.sort(key=lambda s: s["bbox"][0])
            big = [s for s in spans if s["text"].strip()]
            if not big:
                continue
            main = max(s["size"] for s in big)
            txt = ""
            fb = ""
            in_fb = True
            prev = None
            for s in spans:
                t = s["text"]
                if s["size"] < main - 2.5 and re.fullmatch(r"\s*\d{1,2}\s*", t):
                    t = f"⟦{t.strip()}⟧"  # superscript footnote marker
                elif t.strip() == "(*)" and main >= 9.5:
                    t = "⟦*⟧"
                if prev is not None and not txt.endswith((" ", "\t")) and not t.startswith((" ", "\t")) \
                        and s["bbox"][0] - prev["bbox"][2] > 1.5 and not t.startswith("⟦"):
                    txt += " "
                txt += t
                if in_fb and s["text"].strip():
                    if "Bold" in s["font"] or t.startswith("⟦"):
                        fb += t
                    else:
                        in_fb = False
                prev = s
            chars = sum(len(s["text"].strip()) for s in big)
            boldc = sum(len(s["text"].strip()) for s in big if "Bold" in s["font"] or "Black" in s["font"])
            italc = sum(len(s["text"].strip()) for s in big if "Italic" in s["font"])
            out.append(Row(pno, x, y, txt, main, boldc >= chars * 0.9, italc >= chars * 0.6, fb.strip()))
    return out


def paragraphs(rows: list[Row], lead: float) -> list[str]:
    paras: list[str] = []
    prev: Row | None = None
    for r in rows:
        t = clean(r.text)
        if prev is not None and paras and re.search(r"[a-záéíóúñ][\u00ad-]\s*$", prev.text) and re.match(r"[a-záéíóúñ]", t):
            paras[-1] = paras[-1].rstrip("-") + t  # word broken at the line end
            prev = r
            continue
        if not t:
            continue
        if prev is None or not paras:
            paras.append(t)
            prev = r
            continue
        starts = bool(ITEM.match(MARK.sub("", t)) or ART.match(t) or t.startswith("“"))
        if (r.text.startswith(TAB) or re.match(r"^\s*(\d{1,2}|[a-z])\.\t", MARK.sub("", r.text))) and paras:
            paras.append(t)
            prev = r
            continue
        ends = ends_sentence(paras[-1])
        if r.page == prev.page and r.y > prev.y:
            new = (r.y - prev.y) > lead * 1.45 or (starts and ends)
        else:
            new = ends
        if new:
            paras.append(t)
        elif re.search(r"[a-záéíóúñ]-$", paras[-1]) and re.match(r"[a-záéíóúñ]", t):
            paras[-1] = paras[-1][:-1] + t
        else:
            paras[-1] = paras[-1] + " " + t
        prev = r
    return [clean(p) for p in paras]


@dataclass
class Note:
    id: str
    rows: list = field(default_factory=list)

    def text(self) -> str:
        return clean(" ".join(r.text for r in self.rows))


class Edition:
    """units: key -> {"label", "paras": [...], "marks": [(note_id, para_idx)]}; notes: id -> Note."""

    def __init__(self, url: str, style: str):
        self.url = url
        self.style = style
        self.units: dict[str, dict] = {}
        self.notes: dict[str, Note] = {}
        self.heads: list[list[str]] = []  # [heading text, first unit key after it]
        self.order: list[str] = []
        self._parse(rows_of(url))

    def _parse(self, rows: list[Row]) -> None:
        body_rows: dict[str, list[Row]] = {}
        labels: dict[str, str] = {}
        cur: str | None = None
        section = None
        star = 0
        note: Note | None = None
        started = False
        if self.style == "old":
            sizes: dict[float, int] = {}
            for r in rows:
                sizes[round(r.size)] = sizes.get(round(r.size), 0) + len(r.text)
            self.body_size = max(sizes, key=sizes.get)
            rows = [r for r in rows if not re.fullmatch(r"\s*\d+\s*", MARK.sub("", r.text))
                    and not FOOTER.match(r.text)]
        else:
            self.body_size = 10
            rows = [r for r in rows if not (r.size <= 7.6 and r.y > 425)]  # page footers
        star_note = self._star_rows(rows) if self.style == "star" else set()
        old_note = False
        for i, r in enumerate(rows):
            t = r.text.strip()
            plain = MARK.sub("", t).replace(" ", "")
            if not started:
                if plain.upper() == "PREÁMBULO":
                    started = True
                    cur = "preambulo"; labels[cur] = "Preámbulo"; body_rows[cur] = []; self.order.append(cur)
                continue
            if re.match(r"^(OFICIALÍA MAYOR|REFORMAS A LA CONSTITUCIÓN)", t):
                break
            is_note = (r.size < self.body_size - 1.2) or (i in star_note)
            if self.style == "old":
                # checkpoint editions: notes are dropped. Their notes are small/italic, or start with
                # "(*)", "*" or "NOTA" and continue in bold or italic rows.
                if is_note or re.match(r"^(\(\*\)|\*|NOTA)", t) or (old_note and (r.bold or r.italic)):
                    old_note = not is_note or old_note
                    continue
                old_note = False
            if is_note:
                if self.style == "footnote":
                    m = re.match(r"^(\d{1,2})(?:\t\s*|\s+(?=[A-ZÁÉÍÓÚ]))(.*)$", r.text.lstrip(" ")) or re.match(r"^(1)\.\s+(La Constitución Política del Perú se promulgó.*)$", t)
                    if m and int(m.group(1)) == len(self.notes) + 1:
                        note = Note(m.group(1))
                        self.notes[note.id] = note
                        r = Row(r.page, r.x, r.y, m.group(2), r.size, r.bold, r.italic)
                    elif t.startswith("»›"):
                        continue
                else:
                    if t.startswith("(*)"):
                        star += 1
                        note = Note(f"s{star}")
                        self.notes[note.id] = note
                        r = Row(r.page, r.x, r.y, t[3:].strip(), r.size, r.bold, r.italic)
                if note is None:
                    raise SystemExit(f"note text before any note: {t!r}")
                note.rows.append(r)
                continue
            if r.size >= self.body_size + 2.5 and not r.first_bold.startswith("Artículo"):
                continue  # display title "CONSTITUCIÓN POLÍTICA DEL PERÚ"
            if r.bold and not MARK.sub("", r.first_bold).startswith("Artículo") and not DISP.match(r.first_bold):
                h = clean(MARK.sub("", t))
                if h.startswith("DISPOSICIONES FINALES"):
                    section = "dft"
                elif h.startswith("DISPOSICIONES TRANSITORIAS"):
                    section = "dte"
                elif h.startswith("DECLARACI"):
                    section = "decl"
                    cur = "declaracion"; labels[cur] = "Declaración"; body_rows[cur] = []; self.order.append(cur)
                    continue
                if section == "decl":
                    body_rows[cur].append(r)  # "EL CONGRESO CONSTITUYENTE DEMOCRÁTICO" line of the declaration
                    continue
                self.heads.append([h, ""])
                cur = None
                continue
            fb = MARK.sub("", r.first_bold)
            m = ART.match(MARK.sub("", t)) if (fb.startswith("Artículo") or (
                self.style == "old" and re.match(r"^Artículo \d+\s*[°º]?\s*(-\s*[A-Z])?\s*[°º]?\s*\.", t))) else None
            d = DISP.match(MARK.sub("", t)) if section in ("dft", "dte") else None
            if m and section is None:
                cur = unit_key(m.group(1), m.group(2))
                if cur in body_rows:
                    raise SystemExit(f"duplicate unit {cur} in {self.url}")
                labels[cur] = unit_label(m.group(1), m.group(2))
                body_rows[cur] = []
                self.order.append(cur)
                r = Row(r.page, r.x, r.y, split_head(t, m.end()), r.size, r.bold, r.italic)
                for h in self.heads:
                    if not h[1]:
                        h[1] = cur
            elif d:
                n = ORD[d.group(1).lower()]
                cur = f"{section}-{n:02d}"
                labels[cur] = ("Disposición final y transitoria " if section == "dft"
                               else "Disposición transitoria especial ") + d.group(1).lower()
                body_rows[cur] = []
                self.order.append(cur)
                r = Row(r.page, r.x, r.y, split_head(t, d.end()), r.size, r.bold, r.italic)
            if cur is None:
                if MARK.sub("", t).strip():
                    raise SystemExit(f"body text outside a unit in {self.url}: {t!r} section={section} heads={self.heads[-3:]}")
                continue
            body_rows[cur].append(r)
        k = 0  # star markers are numbered in order of appearance
        for key in self.order:
            for r in body_rows[key]:
                while "⟦*⟧" in r.text:
                    k += 1
                    r.text = r.text.replace("⟦*⟧", f"⟦s{k}⟧", 1)
        if self.style == "star" and k != len(self.notes):
            raise SystemExit(f"{k} star markers but {len(self.notes)} notes")
        for key in self.order:
            paras = paragraphs(body_rows[key], 12.0 if self.style != "old" else self.body_size * 1.17)
            marks, out = [], []
            for i, p in enumerate(paras):
                for nid in MARK.findall(p):
                    marks.append((nid, i))
                out.append(clean(MARK.sub("", p)))
            self.units[key] = {"label": labels[key], "paras": out, "marks": marks}

    @staticmethod
    def _star_rows(rows: list[Row]) -> set[int]:
        """Rows that belong to inline (*) notes: the bold 8 pt header, then the quoted future text,
        which the publisher indents (x >= 85 pt; the body sits at 43/64 pt). Mostly italic, but
        some quoted rows are roman, so position, not style, decides. A centred bold roman row is
        a heading and ends the note."""
        out: set[int] = set()
        in_note = False
        for i, r in enumerate(rows):
            t = r.text.strip()
            if t.startswith("(*)") and r.size < 8.8:
                in_note = True
                out.add(i)
                continue
            if not in_note:
                continue
            heading = r.bold and not r.italic and r.size >= 9.5
            if r.size < 8.8 or (r.x >= 85 and not heading):
                out.add(i)
            else:
                in_note = False
        return out

    def note_paras(self, nid: str) -> list[str]:
        n = self.notes[nid]
        lead = 8.0 if n.rows and n.rows[0].size < 8.8 else 12.0
        return paragraphs(n.rows, lead)


def words(paras) -> str:
    """Typography-insensitive form for checkpoint comparison."""
    s = " ".join(paras) if not isinstance(paras, str) else paras
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9ñ]+", " ", s)
    return s.strip()
