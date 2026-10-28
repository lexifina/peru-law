"""Parse the Congreso de la República editions of the 1993 Constitution (text PDFs) into units.

Two layouts:
  * "modern" (Congreso editions May 2021 and Dec 2024; same typesetting): narrow column, page
    footers "CONSTITUCIÓN POLÍTICA DEL PERÚ NN" / "NN Edición del Congreso de la República".
    The 2021 edition has numbered footnotes (1..42) at the page foot; the 2024 edition has
    inline "(*)" notes after the annotated paragraph.
  * "old" (Congreso consolidations 2004, 2012, 2015, 2019): used only as word-level checkpoints.

Everything here reads the cache only (pdftotext output of cached bytes).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import fetch

ORD = {
    "primera": 1, "segunda": 2, "tercera": 3, "cuarta": 4, "quinta": 5, "sexta": 6, "séptima": 7,
    "setima": 7, "sétima": 7, "octava": 8, "novena": 9, "décima": 10, "decima": 10,
    "decimoprimera": 11, "undécima": 11, "decimosegunda": 12, "duodécima": 12,
    "decimotercera": 13, "decimocuarta": 14, "decimoquinta": 15, "decimosexta": 16,
}
ORD_RE = "|".join(sorted(ORD, key=len, reverse=True))


def pdftotext_bin() -> str:
    for cand in (shutil.which("pdftotext"), r"C:\Program Files\Git\mingw64\bin\pdftotext.exe"):
        if cand and Path(cand).exists():
            return cand
    raise SystemExit("pdftotext (poppler/xpdf) not found")


def pdf_text(url: str) -> str:
    p = fetch.cached(url)
    if not p:
        raise SystemExit(f"not in cache: {url} (run fetch.py --plan)")
    r = subprocess.run([pdftotext_bin(), "-enc", "UTF-8", "-layout", str(p), "-"], capture_output=True)
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


def clean(s: str) -> str:
    """Normalise publisher typesetting once: NBSP, quotes, dashes, spaces."""
    s = s.replace("\u00a0", " ").replace("\u00ad", "")
    s = s.replace("\u201f", "\u201c").replace("\u00ab", "\u201c").replace("\u00bb", "\u201d")
    s = s.replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u2013", "-").replace("\u2014", "—").replace("\u2212", "-")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


FOOTER = re.compile(r"^\s*(CONSTITUCIÓN POLÍTICA DEL PERÚ \d+|\d+ Edición del Congreso de la República)\s*$")
HEAD = re.compile(r"^(TÍTULO [IVX]+|Capítulo [IVX]+|CAPÍTULO [IVX]+|DISPOSICIONES FINALES Y TRANSITORIAS|"
                  r"DISPOSICIONES TRANSITORIAS|DECLARACIÓN|PREÁMBULO)\b")
MK = r"(?:\s*(⟦[^⟧]+⟧))?"
ART = re.compile(r"^Artículo (\d+)\s*(?:°|º)?\s*(?:-\s*([A-Z]))?\s*(?:°|º)?\s*(?:\.\s*-|\.|-)" + MK + r"\s*")
DISP = re.compile(r"^(" + ORD_RE + r")\s*\.\s*-?" + MK + r"\s*", re.I)
ITEM = re.compile(r"^(\d{1,2}|[a-z])\.\s")


def unit_key(num: str, suf: str | None) -> str:
    return f"art-{int(num):03d}" + (f"-{suf.lower()}" if suf else "")


def unit_label(num: str, suf: str | None) -> str:
    return f"Artículo {int(num)}" + (f"-{suf}" if suf else "")


def ends_sentence(s: str) -> bool:
    return bool(re.search(r"[.:;”\"]\s*(⟦[^⟧]+⟧)?\s*[.:;”]?$", s))


def to_paragraphs(lines: list[tuple[str, bool]]) -> list[str]:
    """lines = (text, blank_before). Join wrapped lines into paragraphs."""
    paras: list[str] = []
    for text, blank in lines:
        t = text.strip()
        if not t:
            continue
        starts_new = bool(ART.match(t) or ITEM.match(t) or DISP.match(t))
        if not paras:
            paras.append(t)
            continue
        prev = paras[-1]
        if (starts_new and ends_sentence(prev)) or (blank and ends_sentence(prev)):
            paras.append(t)
        elif re.search(r"[a-záéíóúñ]-$", prev) and re.match(r"[a-záéíóúñ]", t):
            paras[-1] = prev[:-1] + t
        else:
            paras[-1] = prev + " " + t
    return [clean(p) for p in paras]


class Edition:
    """units: key -> {"label", "paras": [...], "marks": [(note_id, para_idx)]}; notes: id -> text; heads: list."""

    def __init__(self, txt: str, style: str):
        self.style = style
        self.units: dict[str, dict] = {}
        self.notes: dict[str, str] = {}
        self.heads: list[tuple[str, str]] = []  # (heading, first unit after it)
        self.order: list[str] = []
        body = self._split(txt)
        self._segment(body)

    # -- page handling ---------------------------------------------------------------------
    def _split(self, txt: str) -> list[str]:
        pages = txt.split("\f")
        body: list[str] = []
        started = False
        next_fn = 1
        last_fn: str | None = None
        for page in pages:
            lines = [l for l in page.split("\n") if not FOOTER.match(l)]
            if self.style == "footnote":
                cut = len(lines)
                for i, l in enumerate(lines):
                    m = re.match(r"^(\d{1,2}) [A-ZÁÉÍÓÚ]", l) or re.match(r"^(1)\. (?=La Constitución Política del Perú se promulgó)", l)
                    if (m and int(m.group(1)) == next_fn) or l.startswith("»› continúa"):
                        cut = i
                        break
                notes = lines[cut:]
                lines = lines[:cut]
                cur = last_fn
                for l in notes:
                    m = re.match(r"^(\d{1,2}) ([A-ZÁÉÍÓÚ].*)$", l) or re.match(r"^(1)\. (La Constitución Política del Perú se promulgó.*)$", l)
                    if m and int(m.group(1)) == next_fn:
                        cur = m.group(1)
                        next_fn += 1
                        self.notes[cur] = m.group(2) + "\n"
                    elif l.startswith("»› continúa"):
                        continue
                    elif cur:
                        self.notes[cur] += l + "\n"
                last_fn = cur
            body.extend(lines)
        out = []
        for l in body:
            if not started:
                if re.match(r"^\s*PREÁMBULO\s*$", l):
                    started = True
                else:
                    continue
            if re.match(r"^\s*(OFICIALÍA MAYOR|REFORMAS A LA CONSTITUCIÓN POLÍTICA)\s*$", l):
                break
            out.append(l)
        return out

    # -- markers ---------------------------------------------------------------------------
    def _mark_footnotes(self, text: str) -> str:
        pos = 0
        for n in sorted(self.notes, key=int):
            rx = re.compile(r"(?<=[^\s\d(])" + n + r"(?=[\s”:;,.]|$)", re.M)
            m = rx.search(text, pos)
            if not m:
                raise SystemExit(f"footnote marker {n} not found")
            text = text[:m.start()] + f"⟦{n}⟧" + text[m.end():]
            pos = m.start()
        return text

    def _extract_star_notes(self, lines: list[str]) -> list[str]:
        """2024 style: '(*)' marker in body, note block follows. Returns body lines with ⟦sN⟧ markers."""
        out: list[str] = []
        i = 0
        k = 0
        pending: list[str] = []
        while i < len(lines):
            l = lines[i]
            if re.match(r"^\s*\(\*\)\s*\S", l):
                k += 1
                nid = f"s{k}"
                block = [l.strip()[3:].strip()]
                quoted = "“" in l
                i += 1
                while i < len(lines):
                    l2 = lines[i]
                    if not quoted and "“" in l2:
                        quoted = True
                    if not quoted and not l2.strip() and len(block) > 1 and not re.search(r"siguiente:\s*$", block[-1]):
                        # unquoted note ends at the first blank line once its sentence ended
                        if block[-1].rstrip().endswith("."):
                            break
                    block.append(l2.strip())
                    i += 1
                    if quoted and re.search(r"”\s*\.?\s*$", l2):
                        break
                self.notes[nid] = "\n".join(block) + "\n"
                pending.append(nid)
                continue
            out.append(l)
            i += 1
        # assign markers in order: each "(*)" in body text gets the next note id
        text = "\n".join(out)
        n = 0

        def rep(m):
            nonlocal n
            n += 1
            return f"⟦s{n}⟧"
        text = re.sub(r"\(\*\)", rep, text)
        if n != k:
            raise SystemExit(f"star notes: {k} notes but {n} markers")
        return text.split("\n")

    # -- segmentation ----------------------------------------------------------------------
    def _segment(self, body: list[str]) -> None:
        if self.style == "footnote":
            body = self._mark_footnotes("\n".join(body)).split("\n")
        elif self.style == "star":
            body = self._extract_star_notes(body)
        cur: str | None = None
        lines: dict[str, list] = {}
        labels: dict[str, str] = {}
        section = "body"
        blank = False
        in_head = False
        pending_head: list[str] = []
        for raw in body:
            t = raw.strip()
            if not t:
                blank = True
                if in_head and pending_head:
                    in_head = False
                continue
            tm = re.sub(r"⟦[^⟧]+⟧", "", t)
            if HEAD.match(tm) or (in_head and not ART.match(tm) and not DISP.match(tm)):
                if tm.startswith("PREÁMBULO"):
                    cur = "preambulo"; labels[cur] = "Preámbulo"; lines[cur] = []
                    self.order.append(cur)
                    in_head = False
                    blank = False
                    continue
                if tm.startswith("DISPOSICIONES FINALES"):
                    section = "dft"
                elif tm.startswith("DISPOSICIONES TRANSITORIAS"):
                    section = "dte"
                elif tm.startswith("DECLARACIÓN"):
                    section = "decl"
                    cur = "declaracion"; labels[cur] = "Declaración"; lines[cur] = []
                    self.order.append(cur)
                    in_head = False
                    blank = False
                    continue
                if HEAD.match(tm):
                    if pending_head and not in_head:
                        pass
                    in_head = True
                    pending_head = [tm]
                else:
                    pending_head.append(tm)
                self.heads.append((tm, ""))
                blank = True
                continue
            in_head = False
            m = ART.match(t)
            d = DISP.match(t) if section in ("dft", "dte") else None
            if m and section == "body":
                cur = unit_key(m.group(1), m.group(2))
                labels[cur] = unit_label(m.group(1), m.group(2))
                if cur in lines:
                    raise SystemExit(f"duplicate unit {cur}")
                lines[cur] = []
                self.order.append(cur)
                t = (m.group(3) or "") + t[m.end():]  # keep a marker that sits in the heading
            elif d:
                n = ORD[d.group(1).lower()]
                cur = f"{section}-{n:02d}"
                labels[cur] = ("Disposición final y transitoria " if section == "dft" else "Disposición transitoria especial ") + d.group(1).lower()
                lines[cur] = []
                self.order.append(cur)
                t = (d.group(2) or "") + t[d.end():]
            if cur is None:
                continue
            lines[cur].append((t, blank))
            blank = False
        for key in self.order:
            paras = to_paragraphs(lines[key])
            marks = []
            out = []
            for i, p in enumerate(paras):
                for nid in re.findall(r"⟦([^⟧]+)⟧", p):
                    marks.append((nid, i))
                p = clean(re.sub(r"\s*⟦[^⟧]+⟧\s*", lambda mm: " " if mm.group(0).endswith(" ") and mm.group(0).startswith(" ") else "", p))
                out.append(p)
            self.units[key] = {"label": labels[key], "paras": out, "marks": marks}


def words(paras: list[str]) -> str:
    """Typography-insensitive form for checkpoint comparison."""
    import unicodedata
    s = " ".join(paras).lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9ñ]+", " ", s)
    return s.strip()
