"""Texts of the laws that amended the Código Civil after the MINJUS 14th edition (Aug 2014), from official
text-layer sources (El Peruano pages via Congreso bulletins, gob.pe and busquedas.elperuano.pe; Congreso ADLP
texts). Only the cache is read.

law_text(key) -> the law's own text (normalised, one PDF line per line), cut to the law's block where the
                 source holds a whole gazette issue.
quotes(key)   -> {unit key: [quoted text pieces]} for every Código Civil article the law quotes; a piece is the
                 text between "(…)" / "[…]" marks, so a partial quote gives several pieces.
"""
from __future__ import annotations

import html as htmlmod
import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import fetch  # noqa: E402
import fitz  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)

B = "https://www.leyes.congreso.gob.pe/Documentos/"
NL = B + "2016_2021/Boletin_de_Normas_Legales/NL%s.pdf"
TXM = B + "%s/ADLP/Texto_Consolidado/%s-TXM.pdf"

# key: (url, start anchor regex or None, end anchor regex or None, label, title)
SOURCES = {
    "ley-30364": ("https://cdn.www.gob.pe/uploads/document/file/1837927/Primera%20Edicio%CC%81n%20Oficial%20Proteccio%CC%81n%20y%20Violencia%20contra%20las%20Mujeres.pdf?v=1619545873",
                  r"CUARTA\. Modificación del artículo 667 del Código Civil", r"\(Texto según", "MINJUS, Compendio normativo sobre protección y violencia contra las mujeres (1st official ed., 2021), Ley 30364 text"),
    "ley-30403": ("https://cdn.www.gob.pe/uploads/document/file/3542835/Ley%20N%C2%B0%2030403.pdf?v=1661380267", r"LEY N[º°] 30403", r"POR TANTO", "El Peruano page on gob.pe"),
    "ley-30473": (B + "Leyes/30473.pdf", None, r"POR TANTO", "Congreso ADLP (El Peruano page)"),
    "ley-30490": ("https://cdn.www.gob.pe/uploads/document/file/3766931/Ley%20N%C2%B0%2030490.pdf?v=1666119068", r"LEY N[º°] 30490", r"POR TANTO", "El Peruano pages on gob.pe"),
    "dleg-1297": ("https://cdn.www.gob.pe/uploads/document/file/2007460/Decreto%20Legislativo%20N%C2%BA%201297.pdf.pdf?v=1625854123", r"N[º°] 1297", r"POR TANTO", "El Peruano pages on gob.pe (MIMP)"),
    "ley-30550": (TXM % ("2016_2021", "30550"), None, None, "Congreso ADLP text"),
    "dleg-1377": (NL % "20180824", r"DECRETO LEGISLATIVO\s+N[º°]\s*1377", r"POR TANTO", "El Peruano, 24 Aug 2018 (Congreso bulletin copy)"),
    "dleg-1384": (NL % "20180904", r"DECRETO LEGISLATIVO\s+N[º°]\s*1384", r"POR TANTO", "El Peruano, 4 Sep 2018 (Congreso bulletin copy)"),
    "ley-31309": (NL % "20210724", r"LEY\s+N[º°]\s*31309", r"POR TANTO", "El Peruano, 24 Jul 2021 (Congreso bulletin copy)"),
    "ley-31643": (TXM % ("2021_2026", "31643"), None, None, "Congreso ADLP text"),
    "ley-31945": (TXM % ("2021_2026", "31945"), None, None, "Congreso ADLP text"),
    "ley-32006": (TXM % ("2021_2026", "32006"), None, None, "Congreso ADLP text"),
    "dleg-1626": ("https://busquedas.elperuano.pe/dispositivo/NL/2315597-1/", None, r"POR TANTO", "El Peruano (busquedas)"),
}
EXTRA_URLS = [NL % "20180210"]   # D.S. 001-2018-MIMP (reglamento of D.Leg. 1297), sets its entry into force


def norm_line(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.replace(" ", " ").replace("ﬁ ", "fi").replace("ﬂ ", "fl").replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = s.replace("\t", " ")
    return re.sub(r" +", " ", s).strip()


@lru_cache(None)
def law_text(key: str) -> str:
    url, start, end, _ = SOURCES[key]
    p = fetch.cached(url)
    if p is None:
        raise SystemExit("not cached: " + url)
    if url.endswith("/") and "busquedas" in url:
        raw = p.read_text("utf-8", "replace")
        raw = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
        raw = re.sub(r"<br\s*/?>|</p>|</div>", "\n", raw)
        t = htmlmod.unescape(re.sub(r"<[^>]+>", "", raw))
    else:
        t = "\n".join(pg.get_text() for pg in fitz.open(p))
    lines = [norm_line(x) for x in t.split("\n")]
    t = "\n".join(x for x in lines if x)
    if start:
        m = re.search(start, t)
        if not m:
            raise SystemExit(f"{key}: start anchor not found")
        t = t[m.start():]
    if end:
        m = re.search(end, t)
        if m:
            t = t[:m.start()]
    return t


ELL = re.compile(r"\(\s*(?:…|\.\.\.)\s*\)|\[\s*(?:…|\.\.\.)\s*\]")
QART = re.compile(r"(?m)^[“«\"]?(?:[^\n]{0,90}\n)?[“«\"]?\s*Art[íi]culo\s+(\d+)(?:\s*-\s*([A-Z]))?\s*[º°]?\s*(?:\.\s*-|\.|-)")
CODE = re.compile(r"Código\s+Procesal\s+Civil|Código\s+Civil|Código\s+[A-Z][a-zé]+|Decreto\s+Legislativo\s+N?[º°]?\s*\d+|Ley\s+N?[º°]?\s*\d+")


def quotes(key: str) -> dict[str, list[str]]:
    """Article starts in the law's text that sit in a Código Civil context: the last code or law named
    before the article (and after the previous article) is the Código Civil."""
    t = law_text(key)
    out: dict[str, list[str]] = {}
    starts = list(QART.finditer(t))
    ctx_cc = False
    prev_end = 0
    for i, m in enumerate(starts):
        names = [x.group(0) for x in CODE.finditer(t, prev_end, m.start())
                 if not re.match(r"Decreto\s+Legislativo\s+N?[º°]?\s*295$|Decreto\s+Legislativo\s+N?[º°]?\s*" + key.split("-")[1] + "$", x.group(0))]
        if names:
            ctx_cc = bool(re.fullmatch(r"Código\s+Civil", names[-1]))
        nxt = starts[i + 1].start() if i + 1 < len(starts) else len(t)
        seg = t[m.start():nxt]
        prev_end = m.end()
        if not ctx_cc:
            continue
        k = "art-%04d%s" % (int(m.group(1)), ("-" + m.group(2).lower()) if m.group(2) else "")
        pieces = [p.strip(" “”«»\"") for p in ELL.split(seg) if p.strip(" “”«»\"\n")]
        out.setdefault(k, []).extend(pieces)
    return out


def flat(s: str) -> str:
    """Letters and digits only, case-folded: robust containment key across typesetting."""
    s = unicodedata.normalize("NFC", s).casefold()
    s = re.sub(r"(\d)\s*[º°]", r"\1", s)
    return re.sub(r"[^0-9a-záéíóúüñ]", "", s)
