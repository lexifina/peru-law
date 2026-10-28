"""Parse the cached sources into corpus.d/50-codes.json (Código Civil, Ley 29733).

Reads only ../.cache (no network). Deterministic. Writes the part atomically
(.tmp then rename). Run:  python -X utf8 codes/parse_codes.py [--report]
"""
from __future__ import annotations

import hashlib
import html as htmlmod
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import fetch  # noqa: E402  (cache paths only; parse never downloads)
import fitz  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)

OUT = ROOT / "corpus.d" / "50-codes.json"
if "--out" in sys.argv:
    OUT = Path(sys.argv[sys.argv.index("--out") + 1]).resolve()
class _R(list):
    def append(self, x):
        super().append(x)
        if "--report" in sys.argv:
            print(x, flush=True)


REPORT: list[str] = _R()

# ---- sources (all read from the cache) -------------------------------------------------
WB = "https://web.archive.org/web/{ts}id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma={n}"
SRC = {
    # Editora Peru, Normas Legales Actualizadas: Codigo Civil (copy kept by FAOLEX; the
    # El Peruano server now serves this series with every byte >= 0x80 replaced, see PROGRESS.md)
    "cc_nla": "https://faolex.fao.org/docs/pdf/per205198.pdf",
    # D.Leg. 1626 as published in El Peruano (busquedas.elperuano.pe, HTML)
    "dleg1626": "https://busquedas.elperuano.pe/dispositivo/NL/2315597-1/",
    # Ley 32228, Congreso ADLP text
    "ley32228": "https://www.leyes.congreso.gob.pe/Documentos/2021_2026/ADLP/Texto_Consolidado/32228-TXM.pdf",
    # Editora Peru NLA: Ley 29733 (+ reglamento); Wayback raw captures, pinned
    "dp_nla_2026": WB.format(ts="20260721055737", n=23),
    "dp_nla_2025": WB.format(ts="20260409192208", n=23),
    # ANPD (MINJUS) published copy of Ley 29733 with original and amended texts (gob.pe, 2023)
    "dp_anpd": "https://cdn.www.gob.pe/uploads/document/file/2011398/Ley%20N%C2%BA%2029733%20-%20Ley%20de%20protecci%C3%B3n%20de%20datos%20personales.pdf.pdf?v=1683928275",
    # MINSA-hosted copy of the same text before D.Leg. 1353 (2016), cross-check only
    "dp_minsa": "https://www.minsa.gob.pe/Recursos/OGTI/SINADEF/Ley-29733.pdf",
    # El Peruano 15 Sep 2017 page with DS 019-2017-JUS (sets D.Leg. 1353 in force), hosted by SUNAT
    "ds019": "https://www.sunat.gob.pe/legislacion/procedim/normasadua/normasociada/gja-00.02/ctrlCambios/anexos/DS019-2017-JUS.pdf",
    # El Peruano 22 Mar 2013 Normas Legales with DS 003-2013-JUS (reglamento), ANPD copy
    "ds003": "https://cdn.www.gob.pe/uploads/document/file/2011287/Reglamento%20de%20la%20Ley%20No%2029733%2C%20Ley%20de%20Protecci%C3%B3n%20de%20Datos%20Personales.pdf?v=1626124830",
}


def cpath(key: str) -> Path:
    p = fetch.cached(SRC[key])
    if not p:
        raise SystemExit(f"not in cache: {SRC[key]} (run codes/cfetch.py --plan)")
    return p


def sha(key: str) -> str:
    return hashlib.sha256(cpath(key).read_bytes()).hexdigest()


# ---- text normalisation ------------------------------------------------------------------
def norm(s: str) -> str:
    s = s.replace(" ", " ").replace("­", "").replace("ﬁ", "fi").replace("ﬂ", "fl")
    s = s.replace("‘", "'").replace("’", "'").replace("–", "-").replace("—", "-")
    s = s.replace("\t", " ")
    s = re.sub(r"[ ]+", " ", s)
    return s.strip()


def cmpkey(s: str) -> str:
    """Typography-insensitive comparison key: words only, case-folded."""
    s = s.replace("“", '"').replace("”", '"').replace("?", " ")
    s = re.sub(r"[\"'«»]", " ", s)
    s = re.sub(r"\s+([.,;:)])", r"\1", s)
    return " ".join(s.casefold().split())


# ---- Editora Peru NLA two-column reader --------------------------------------------------
def is_note_span(sp) -> bool:
    """Editora Peru prints editorial notes in bold italic 8 pt."""
    return "Italic" in sp["font"] and sp["size"] <= 8.5


def nla_lines(path: Path, first: int, last: int | None):
    """Yield dict(pno, col, base, right, x0, x1, text, note, block, centered) per visual line, reading order.

    `text` is the body text of the line, `note` the editorial-note text on it (bold italic 8 pt)."""
    d = fitz.open(path)
    last = d.page_count if last is None else last
    bid = 0
    for pno in range(first, last):
        p = d[pno]
        h, w = p.rect.height, p.rect.width
        top, bottom, mid = 72 * h / 779.5, 762 * h / 779.5, w / 2
        blocks = []
        for b in p.get_text("dict")["blocks"]:
            if b["type"] != 0:
                continue
            x0, y0 = b["bbox"][0], b["bbox"][1]
            if y0 < top or y0 > bottom:
                continue
            col = 0 if x0 < mid - 5 else 1
            rows: list[list] = []   # [y, x0, x1, [(x, body, note)]]
            for ln in b["lines"]:
                body = "".join(sp["text"] for sp in ln["spans"] if not is_note_span(sp))
                note = "".join(sp["text"] for sp in ln["spans"] if is_note_span(sp))
                if not (body.strip() or note.strip()):
                    continue
                y = ln["bbox"][3]
                if rows and abs(rows[-1][0] - y) < 2.5:
                    rows[-1][1] = min(rows[-1][1], ln["bbox"][0])
                    rows[-1][2] = max(rows[-1][2], ln["bbox"][2])
                    rows[-1][3].append((ln["bbox"][0], body, note))
                else:
                    rows.append([y, ln["bbox"][0], ln["bbox"][2], [(ln["bbox"][0], body, note)]])
            if rows:
                blocks.append((col, y0, x0, rows))
        blocks.sort(key=lambda r: (r[0], r[1], r[2]))
        for col in (0, 1):
            cb = [bl for bl in blocks if bl[0] == col]
            if not cb:
                continue
            base = min(r[1] for bl in cb for r in bl[3])
            right = max(r[2] for bl in cb for r in bl[3])
            for _, _, bx0, rows in cb:
                bid += 1
                centered = all(r[1] > base + 20 for r in rows)
                for y, x0, x1, parts in rows:
                    parts.sort(key=lambda q: q[0])
                    body = " ".join(q[1].strip() for q in parts if q[1].strip())
                    note = " ".join(q[2].strip() for q in parts if q[2].strip())
                    yield {"pno": pno, "col": col, "base": base, "right": right, "x0": x0, "x1": x1,
                           "text": body, "note": note, "block": bid, "centered": centered}


MARK = re.compile(r"^(“|\")?(Artículo\s|\d+(\.\d+)*\.-?\s|[a-z]\)\s)")


def nla_paragraphs(path: Path, first: int, last: int | None):
    """Group visual lines into paragraphs: dict(kind, text, notes, note_after, block, single)."""
    paras: list[dict] = []
    prev = None
    after_note = False
    for L in nla_lines(path, first, last):
        text, note = L["text"].strip(), L["note"].strip()
        if not text:
            if note and paras:
                paras[-1]["notes"].append(note) if paras[-1]["note_after"] else (
                    paras[-1].__setitem__("note_after", True), paras[-1]["notes"].append(note))
                after_note = True
            continue
        if L["centered"]:
            if paras and paras[-1]["kind"] == "struct" and paras[-1]["block"] == L["block"] and not after_note:
                paras[-1]["text"] += " " + text
            else:
                paras.append({"kind": "struct", "text": text, "block": L["block"], "notes": [], "note_after": False})
            if note:
                paras[-1]["notes"].append(note)
                paras[-1]["note_after"] = True
            prev = None
            after_note = bool(note)
            continue
        new = prev is None or after_note
        if not new:
            if L["x0"] > L["base"] + 6:
                new = True
            elif (prev["pno"], prev["col"]) == (L["pno"], L["col"]) and prev["x1"] < prev["right"] - 18:
                new = True
            elif MARK.match(text) and re.search(r"[.:;”\"]\s*$", prev["text"]):
                new = True
        if new or not paras or paras[-1]["kind"] != "para":
            paras.append({"kind": "para", "text": text, "block": L["block"], "blocks": {L["block"]},
                          "notes": [], "note_after": False})
        else:
            paras[-1]["text"] += " " + text
            paras[-1]["blocks"].add(L["block"])
        if note:
            paras[-1]["notes"].append(note)
            paras[-1]["note_after"] = True
        after_note = bool(note)
        prev = L
    for p in paras:
        p["text"] = norm(re.sub(r"\s*\(\*\)\s*", " ", p["text"]))
        p["note"] = norm(" ".join(p["notes"])) if p["notes"] else None
    count: dict[int, int] = {}
    for p in paras:
        if p["kind"] == "para":
            for bb in p["blocks"]:
                count[bb] = count.get(bb, 0) + 1
    for p in paras:
        if p["kind"] == "para":
            p["single"] = len(p["blocks"]) == 1 and count[p["block"]] == 1
    return paras


NOTE = re.compile(r"\s*\(\*\)\s*")


def split_note(text: str):
    """Return (text before the first note marker, note text or None)."""
    m = re.search(r"\(\*\)", text)
    if not m:
        return text, None
    return text[: m.start()].rstrip(), text[m.end():].strip()


def unquote_unit(lines: list[str], closes: list[int]) -> list[str]:
    """Remove the amendment quotes: a closing ” right before a note and its opening “."""
    s = "\n".join(lines)
    # positions in s of closing quotes (end-of-line indices recorded by caller)
    offs = []
    acc = 0
    for i, ln in enumerate(lines):
        if i in closes:
            offs.append(acc + len(ln))
        acc += len(ln) + 1
    chars = list(s)
    for end in sorted(offs, reverse=True):
        j = end - 1
        while j >= 0 and chars[j] in " .":
            j -= 1
        if j < 0 or chars[j] not in "”\"":
            continue
        # drop closing quote (keep a following period if any)
        chars[j] = ""
        depth = 0
        k = j - 1
        while k >= 0:
            c = chars[k]
            if c == "”":
                depth += 1
            elif c == "“":
                if depth == 0:
                    chars[k] = ""
                    break
                depth -= 1
            k -= 1
    out = "".join(chars).split("\n")
    out = [re.sub(r"\s+\.$", ".", ln).strip() for ln in out]
    return out


def fix_quotes(s: str) -> str:
    return s.replace("“", '"').replace("”", '"')


# ---- Codigo Civil ------------------------------------------------------------------------
ART_CC = re.compile(r"^(“|\")?Artículo\s+(\d+)\s*(?:-\s*([A-Z]))?\s*°?\s*\.?\s*-\s*(.*)$")
ART_TP = re.compile(r"^(“|\")?Artículo\s+([IVX]+)\s*\.?\s*-\s*(.*)$")
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10}


def cc_parse():
    path = cpath("cc_nla")
    d = fitz.open(path)
    first = next(i for i in range(15, 30) if "TÍTULO PRELIMINAR" in d[i].get_text() and "Abrogación de la ley" in d[i].get_text())
    paras = nla_paragraphs(path, first, None)
    # body starts at the TÍTULO PRELIMINAR heading, ends before the Comisión's thanks
    start = next(i for i, p in enumerate(paras) if p["kind"] == "struct" and p["text"].startswith("TÍTULO PRELIMINAR"))
    stop = next(i for i, p in enumerate(paras) if "expresa su agradecimiento" in p["text"])
    paras = paras[start:stop]
    units: "OrderedDict[str, dict]" = OrderedDict()
    struct: list[str] = []
    notes_by_unit: dict[str, list[str]] = {}
    cur = None
    pending_sumilla = None
    skip_pending = False
    log = {"pending_dropped": 0, "stub_lines_dropped": 0, "derogated": [], "dupes": []}
    for i, p in enumerate(paras):
        t = p["text"]
        if p["kind"] == "struct":
            body, note = t, p["note"]
            if body:
                struct.append(fix_quotes(body.strip("“” ")))
            cur = None
            pending_sumilla = None
            continue
        if skip_pending:
            # a not-yet-in-force text quoted after "... será el siguiente:"; skip through its closing quote
            log["pending_dropped"] += 1
            if re.search(r"[”\"]\s*\.?\s*$", t) or (i + 1 < len(paras) and ART_CC.match(paras[i + 1]["text"]) and not paras[i + 1]["text"].startswith("“")):
                skip_pending = False
            continue
        m = ART_CC.match(t) or ART_TP.match(t)
        if m:
            if m.re is ART_TP:
                key = "tp-%02d" % ROMAN[m.group(2)]
            else:
                key = "art-%04d" % int(m.group(2)) + ("-" + m.group(3).lower() if m.group(3) else "")
            if key in units:
                log["dupes"].append(key)
                cur = None
                continue
            cur = {"lines": [], "closes": []}
            units[key] = cur
            notes_by_unit[key] = []
            if pending_sumilla:
                cur["lines"].append(pending_sumilla)
            pending_sumilla = None
        elif cur is None or (p.get("single") and len(t) <= 160 and not re.search(r"[.:;,]\s*[”\"]?\s*$", t)
                             and i + 1 < len(paras) and paras[i + 1]["kind"] == "para"
                             and (ART_CC.match(paras[i + 1]["text"]) or ART_TP.match(paras[i + 1]["text"]))):
            body, note = t, p["note"]
            pending_sumilla = body.strip() or None
            if cur is None and not pending_sumilla:
                pass
            cur = None if pending_sumilla else cur
            continue
        body, note = t, p["note"]
        if note is not None:
            notes_by_unit[key].append(note)
            if re.search(r"siguiente\s*:\s*$", note):
                skip_pending = True
        stub = re.fullmatch(r"(“|\")?(\d+\.-?|[a-z]\))", body.strip())
        if stub:
            log["stub_lines_dropped"] += 1
            continue
        if body:
            if note is not None:
                cur["closes"].append(len(cur["lines"]))
            cur["lines"].append(body)
    out = OrderedDict()
    for key, u in units.items():
        lines = unquote_unit(u["lines"], u["closes"])
        lines = [fix_quotes(ln) for ln in lines if ln]
        # an article whose only content is its number was repealed: no file
        rest = re.sub(r"^(Artículo\s+\S+\s*\.?-)", "", lines[-1]).strip() if len(lines) == 1 else "x"
        if not lines or not rest:
            log["derogated"].append(key)
            continue
        out[key] = "\n".join(lines) + "\n"
    return out, struct, notes_by_unit, log


def html_text(raw: str) -> str:
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</div>", "\n", s)
    s = htmlmod.unescape(re.sub(r"<[^>]+>", "", s))
    return "\n".join(norm(x) for x in s.split("\n") if norm(x))


def quoted_articles(text: str) -> dict[str, list[str]]:
    """Articles quoted in an amending law: “Artículo N.- Sumilla\\nbody”."""
    out = {}
    for m in re.finditer(r"“Artículo\s+(\d+)(?:-([A-Z]))?\.-\s*(.*?)”", text, re.S):
        key = "art-%04d" % int(m.group(1)) + ("-" + m.group(2).lower() if m.group(2) else "")
        lines = [norm(x) for x in m.group(3).split("\n") if norm(x)]
        out[key] = lines
    return out


def amended_unit(num: str, lines: list[str]) -> str:
    """Lay out an amending law's article the way the NLA edition does: sumilla line, then 'Artículo N.- body'."""
    sumilla, body = lines[0], lines[1:]
    return "\n".join([sumilla, f"Artículo {num}.- " + (body[0] if body else "")] + body[1:]) + "\n"


def pdf_text(key: str) -> str:
    d = fitz.open(cpath(key))
    return "\n".join(p.get_text() for p in d)


# ---- Ley 29733 ---------------------------------------------------------------------------
ORD = ["PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA", "SEXTA", "SÉTIMA", "OCTAVA", "NOVENA", "DÉCIMA",
       "UNDÉCIMA", "DUODÉCIMA"]
ART_DP = re.compile(r"^(“|\")?Artículo\s+(\d+)\s*\.-?\s*(.*)$")
DCF_DP = re.compile(r"^(“|\")?(%s)\.\s*(.*)$" % "|".join(o.capitalize() for o in ORD), re.I)


def dp_key(t: str):
    m = ART_DP.match(t)
    if m:
        return "art-%03d" % int(m.group(2))
    m = DCF_DP.match(t)
    if m:
        return "dcf-%02d" % (ORD.index(m.group(2).upper()) + 1)
    return None


def dp_parse_nla(key: str):
    path = cpath(key)
    paras = nla_paragraphs(path, 0, None)
    start = next(i for i, p in enumerate(paras) if p["text"].startswith("Título Preliminar: Disposiciones generales"))
    stop = next(i for i, p in enumerate(paras) if p["text"].startswith("Comuníquese al señor Presidente"))
    paras = paras[start:stop]
    units: "OrderedDict[str, dict]" = OrderedDict()
    struct: list[str] = []
    notes: dict[str, list[str]] = {}
    sumario: list[str] = []
    cur = None
    in_dcf = False
    for p in paras:
        t = p["text"]
        if p["kind"] == "struct" or (t.isupper() and len(t) < 90 and not dp_key(t)):
            body, note = t, p["note"]
            body = body.strip("“” ")
            if body:
                struct.append(fix_quotes(body))
            if note:
                notes.setdefault("estructura", []).append(note)
            in_dcf = in_dcf or "COMPLEMENTARIAS" in t
            cur = None
            continue
        k = dp_key(t) if (not in_dcf or not ART_DP.match(t)) else dp_key(t)
        if k and (k.startswith("art") or in_dcf):
            cur = {"lines": [], "closes": []}
            units[k] = cur
            notes[k] = []
        if cur is None:
            body, note = t, p["note"]
            sumario.append(body)
            continue
        body, note = t, p["note"]
        if note is not None:
            notes[k if k else list(units)[-1]].append(note)
        kk = list(units)[-1]
        if body:
            if note is not None:
                cur["closes"].append(len(cur["lines"]))
            cur["lines"].append(body)
    out = OrderedDict()
    for k, u in units.items():
        lines = [fix_quotes(x) for x in unquote_unit(u["lines"], u["closes"]) if x]
        out[k] = "\n".join(lines) + "\n"
    return out, struct, notes, sumario


def dp_parse_anpd():
    """Original texts that D.Leg. 1353 replaced, from the ANPD copy: unit text up to its '(*)' note."""
    raw = pdf_text("dp_anpd")
    lines = raw.split("\n")
    old: dict[str, list[str]] = {}
    heading_old = None
    i = 0
    cur_key, buf = None, []
    paras: list[str] = []

    def flush_para(acc):
        if acc:
            paras.append(norm(" ".join(acc)))

    # rebuild paragraphs: a paragraph starts at a line with >= 4 leading spaces
    acc: list[str] = []
    skip_conc = False
    for ln in lines:
        if ln.startswith("CONCORDANCIAS:"):
            flush_para(acc); acc = []
            skip_conc = True
            continue
        if skip_conc and (re.match(r"^\s{8,}\S", ln) or not ln.strip()):
            continue
        skip_conc = False
        if not ln.strip():
            continue
        if re.match(r"^\s{4,}\S", ln) or ln.startswith("(*)") or re.match(r"^(TÍTULO|[A-ZÁÉÍÓÚÑ ,]{12,}$)", ln):
            flush_para(acc); acc = []
        acc.append(ln.strip())
    flush_para(acc)
    # walk: a unit starts at 'Artículo N.' / ordinal DCF; it is "original then modified" when a
    # '(*) Artículo modificado ...' paragraph follows
    out: dict[str, list[str]] = {}
    for j, p in enumerate(paras):
        k = dp_key(p.lstrip("?“\" "))
        if k and not p.startswith("?") and not p.startswith("“"):
            cur_key, buf = k, [p]
            continue
        if p.startswith("(*) Artículo modificado") and cur_key and cur_key not in out:
            out[cur_key] = buf[:]
            cur_key = None
            continue
        if p.startswith("(*) Denominación modificada"):
            heading_old = paras[j - 1]
            continue
        if cur_key:
            buf.append(p)
    # trim the trailing '(*)' marker on the last paragraph
    for k, v in out.items():
        v[-1] = re.sub(r"\s*\(\*\)\s*$", "", v[-1])
        out[k] = [fix_quotes(norm(x)) for x in v]
    heading_old = re.sub(r"\s*\(\*\)\s*$", "", heading_old or "")
    return out, heading_old, paras


def dp_minsa_paras():
    raw = pdf_text("dp_minsa")
    return cmpkey(raw)


# ---- assemble ----------------------------------------------------------------------------
def law(label, title, kind, enacted, published, url, note=None):
    return {"label": label, "title": title, "kind": kind, "enacted": enacted, "published": published, "url": url,
            "temporary_until": None, "restores": None, "note": note}


def main():
    report = "--report" in sys.argv
    laws = OrderedDict()
    decisions: list[str] = []
    acts = []

    # ---------------- Código Civil ----------------
    cc, cc_struct, cc_notes, cc_log = cc_parse()
    units1 = OrderedDict((k, {"label": label_cc(k), "kind": "art", "text": v}) for k, v in cc.items())
    units1["estructura"] = {"label": "Estructura (libros, secciones, títulos, capítulos)", "kind": "structure",
                            "text": "\n".join(cc_struct) + "\n"}
    REPORT.append(f"CC: {len(cc)} article units, {len(cc_struct)} heading lines, log={ {k: (v if isinstance(v, int) else len(v)) for k, v in cc_log.items()} }")
    REPORT.append(f"CC derogated (no file): {cc_log['derogated'][:40]}")
    REPORT.append(f"CC duplicate article starts dropped (pending texts): {cc_log['dupes']}")

    # D.Leg. 1626: arts 2033, 2040, 2042 in force 2024-08-16 (in the NLA text); 2037, 2038 on 2024-11-13
    dl = html_text(cpath("dleg1626").read_text("utf-8", "replace"))
    q1626 = quoted_articles(dl)
    for k in ("art-2033", "art-2040", "art-2042"):
        if cmpkey(amended_unit(k[4:].lstrip("0"), q1626[k])) != cmpkey(units1[k]["text"]):
            REPORT.append(f"MISMATCH D.Leg 1626 {k}:\n  NLA: {units1[k]['text']!r}\n  DL : {q1626[k]!r}")
        else:
            REPORT.append(f"ok: D.Leg 1626 {k} text equals the NLA text")
    units2 = OrderedDict((k, dict(v)) for k, v in units1.items())
    for k in ("art-2037", "art-2038"):
        units2[k] = {"label": label_cc(k), "kind": "art", "text": amended_unit(k[4:].lstrip("0"), q1626[k])}
    # Ley 32228: incorporates art. 233-A
    t32228 = pdf_text("ley32228")
    q32228 = quoted_articles(t32228)
    units3 = OrderedDict((k, dict(v)) for k, v in units2.items())
    units3["art-0233-a"] = {"label": "Art. 233-A", "kind": "art",
                            "text": amended_unit("233-A", q32228["art-0233-a"])}
    units3 = OrderedDict(sorted(units3.items(), key=lambda kv: sort_cc(kv[0])))

    laws["dleg-295"] = law("Decreto Legislativo 295", "Código Civil", "decree", "1984-07-24", "1984-07-25",
                           "https://www.leyes.congreso.gob.pe/Documentos/DecretosLegislativos/00295.pdf")
    laws["dleg-1626"] = law("Decreto Legislativo 1626", "Decreto Legislativo que modifica los artículos 2033, 2037, 2038, 2040 y 2042 del Código Civil",
                            "decree", "2024-08-14", "2024-08-15", SRC["dleg1626"])
    laws["ley-32228"] = law("Ley 32228", "Ley que modifica el Código Civil, Decreto Legislativo 295, para incorporar los principios generales de los procesos en materia de familia",
                            "law", "2025-01-07", "2025-01-08",
                            "https://www.leyes.congreso.gob.pe/Documentos/2021_2026/ADLP/Texto_Consolidado/32228-TXM.pdf")
    acts.append({
        "slug": "codigo-civil", "short": "CC", "title": "Código Civil (Decreto Legislativo 295)",
        "url": SRC["cc_nla"], "first_law": None, "earlier_laws": ["dleg-295"],
        "versions": [
            {"from": "2024-08-16", "source_url": SRC["cc_nla"], "sha256": sha("cc_nla"), "units": units1, "credits": {},
             "note": ("Oldest version available: the Editora Perú 'Normas Legales Actualizadas' edition of the Código Civil, "
                      "which includes amendments published up to 15 August 2024 (D.Leg. 1626). The code was enacted by "
                      "D.Leg. 295 (in force 14 November 1984) and amended some 400 times since; that earlier history is not "
                      "rebuilt here. Texts of amendments not yet in force (D.Leg. 1400 garantía mobiliaria) are left out.")},
            {"from": "2024-11-13", "source_url": SRC["dleg1626"], "sha256": sha("dleg1626"), "units": units2,
             "credits": {"art-2037": ["dleg-1626"], "art-2038": ["dleg-1626"]},
             "note": "D.Leg. 1626, única disposición complementaria final: the changes to arts. 2037 and 2038 take effect 90 days after publication (15 August 2024)."},
            {"from": "2025-01-09", "source_url": SRC["ley32228"], "sha256": sha("ley32228"), "units": units3,
             "credits": {"art-0233-a": ["ley-32228"]}, "note": None},
        ],
    })

    # ---------------- Ley 29733 ----------------
    cur, struct, notes, sumario = dp_parse_nla("dp_nla_2026")
    cur25, struct25, _, _ = dp_parse_nla("dp_nla_2025")
    for k in sorted(set(cur) | set(cur25)):
        if cmpkey(cur.get(k, "")) != cmpkey(cur25.get(k, "")):
            REPORT.append(f"DP NLA 2025 vs 2026 differ at {k}")
    modified = sorted(k for k, v in notes.items() if k != "estructura" and any("1353" in n for n in v))
    old, heading_old, anpd_paras = dp_parse_anpd()
    REPORT.append(f"DP: {len(cur)} units now; modified by D.Leg 1353 per NLA notes: {modified}; ANPD originals found: {sorted(old)}")
    if sorted(old) != modified:
        REPORT.append(f"MISMATCH DP modified sets: NLA {modified} vs ANPD {sorted(old)}")
    # cross-check: units not modified must be identical in the ANPD/MINSA texts (word level)
    anpd_all = cmpkey("\n".join(anpd_paras))
    minsa_all = dp_minsa_paras()
    bad = []
    for k, v in cur.items():
        if k in modified:
            continue
        for ln in v.split("\n"):
            if ln and cmpkey(ln) not in anpd_all:
                bad.append((k, "anpd", ln[:80]))
            if ln and cmpkey(ln) not in minsa_all:
                bad.append((k, "minsa", ln[:80]))
    for k in modified:
        for ln in old.get(k, []):
            if cmpkey(ln) not in minsa_all:
                bad.append((k, "minsa-old", ln[:80]))
    REPORT.append(f"DP unchanged-unit check: {len(bad)} line(s) not found")
    for b in bad[:30]:
        REPORT.append(f"  {b}")

    def dp_label(k):
        if k.startswith("art-"):
            return "Art. %d" % int(k[4:])
        if k.startswith("dcf-"):
            return "Disposición complementaria final %s" % ORD[int(k[4:]) - 1].lower()
        return k

    def dp_units(texts, struct_lines, sumario_lines):
        u = OrderedDict()
        u["sumario"] = {"label": "Sumario", "kind": "preamble", "text": "\n".join(sumario_lines) + "\n"}
        u["estructura"] = {"label": "Estructura (títulos)", "kind": "structure", "text": "\n".join(struct_lines) + "\n"}
        for k, v in texts.items():
            u[k] = {"label": dp_label(k), "kind": "art" if k.startswith("art") else "final", "text": v}
        return u

    orig = OrderedDict(cur)
    for k in modified:
        orig[k] = "\n".join(old[k]) + "\n"
    struct_old = list(struct)
    new_heading = None
    for n_i, line in enumerate(struct):
        if line.startswith("OBLIGACIONES DEL TITULAR Y DEL ENCARGADO DE TRATAMIENTO"):
            new_heading = line
            struct_old[n_i] = heading_old.strip("“”\" ")
    REPORT.append(f"DP Title IV heading: old={struct_old[struct.index(new_heading)] if new_heading else None!r} new={new_heading!r}")
    v1 = dp_units(orig, struct_old, sumario)
    v3 = dp_units(cur, struct, sumario)
    dp_credits = {k: ["dleg-1353"] for k in modified}
    dp_credits["estructura"] = ["dleg-1353"]
    commence = [k for k in v1 if k not in ("sumario", "estructura")]
    laws["ley-29733"] = law("Ley 29733", "Ley de Protección de Datos Personales", "law", "2011-07-02", "2011-07-03",
                            "https://www.leyes.congreso.gob.pe/Documentos/Leyes/29733.pdf")
    laws["ds-003-2013-jus"] = law("Decreto Supremo 003-2013-JUS", "Aprueban el Reglamento de la Ley N° 29733, Ley de Protección de Datos Personales",
                                  "decree", "2013-03-21", "2013-03-22", SRC["ds003"],
                                  note=("No words changed. Under the duodécima disposición complementaria final of Ley 29733, the provisions "
                                        "not already in force (all but Título II, art. 32 first paragraph and the 1st-4th, 9th and 10th "
                                        "final provisions) took effect 30 business days after this reglamento was published on 22 March 2013."))
    laws["dleg-1353"] = law("Decreto Legislativo 1353", "Decreto Legislativo que crea la Autoridad Nacional de Transparencia y Acceso a la Información Pública, fortalece el Régimen de Protección de Datos Personales y la regulación de la gestión de intereses",
                            "decree", "2017-01-06", "2017-01-07", "https://www.leyes.congreso.gob.pe/Documentos/DecretosLegislativos/01353.pdf")
    deferred = [k for k in commence if not (k in [f"art-{n:03d}" for n in range(13, 19)] or k == "art-032"
                                             or k in ("dcf-01", "dcf-02", "dcf-03", "dcf-04", "dcf-09", "dcf-10"))]
    acts.append({
        "slug": "proteccion-datos-personales", "short": "LPDP", "title": "Ley 29733, Ley de Protección de Datos Personales",
        "url": "https://www.leyes.congreso.gob.pe/Documentos/Leyes/29733.pdf", "first_law": "ley-29733", "earlier_laws": [],
        "versions": [
            {"from": "2011-07-04", "source_url": SRC["dp_anpd"], "sha256": sha("dp_anpd"), "units": v1, "credits": {},
             "note": ("As enacted (published 3 July 2011). Only Título II, art. 32 first paragraph and the 1st-4th, 9th and "
                      "10th final provisions were in force from 4 July 2011; the rest from 8 May 2013 (see that commit). Texts "
                      "replaced in 2017 are taken from the ANPD/MINJUS copy, which prints each original before its amended text.")},
            {"from": "2013-05-08", "source_url": SRC["ds003"], "sha256": sha("ds003"), "units": v1,
             "credits": {k: ["ds-003-2013-jus"] for k in deferred}, "note": "Commencement of the remaining provisions; no words changed."},
            {"from": "2017-09-16", "source_url": SRC["dp_nla_2026"], "sha256": sha("dp_nla_2026"), "units": v3,
             "credits": dp_credits,
             "note": ("D.Leg. 1353 (published 7 January 2017) took effect the day after the decree approving its reglamento "
                      "(D.S. 019-2017-JUS, El Peruano 15 September 2017).")},
        ],
    })

    decisions += [
        "Codes part (Código Civil, Ley 29733) is written by codes/parse_codes.py into corpus.d/50-codes.json; SPIJ is not used (unreachable).",
        "Código Civil: no official source gives its text before 2024 in a usable form (the El Peruano 1984 publication and the ADLP copy of D.Leg. 295 are scans; the amendments number about 400), so its history starts at the Editora Perú NLA edition current to 15 August 2024 as the oldest version available, credited to the publisher.",
        "Código Civil NLA edition is read from the copy kept by FAOLEX (faolex.fao.org/docs/pdf/per205198.pdf); El Peruano's own obtenerDocumento endpoint currently serves these PDFs with every byte >= 0x80 replaced by U+FFFD, and no Wayback capture of the Código Civil edition was found.",
        "Código Civil text in force: where the NLA edition prints a pending text after 'el nuevo texto será el siguiente:' (D.Leg. 1400, garantía mobiliaria, not yet in force), the pending text is dropped and the in-force text kept.",
        "Código Civil units: one file per article (art-NNNN, art-NNNN-a for lettered articles; tp-NN for the Título Preliminar), first line the sumilla (article heading) as printed in the official edition, then the article; repealed articles have no file; book/section/title/chapter headings are in 'estructura'.",
        "Código Civil: amendment quotes (“…” around amended text) and the edition's (*) notes are removed from the text; Ley 25362 (1991) authorised sumillas in official editions, so they are kept.",
        "D.Leg. 1626: arts. 2033, 2040 and 2042 took effect the day after publication (already in the NLA text, checked word for word against El Peruano); arts. 2037 and 2038 took effect 90 days after publication, 13 November 2024, applied from the El Peruano text.",
        "Ley 32228 (art. 233-A): published 8 January 2025 (ADLP index; the Congreso text header misprints 2024), in force 9 January 2025 under Const. art. 109.",
        "Código Civil after 9 January 2025: the Congreso ADLP index (laws up to Ley 32537, 26 December 2025) lists no further law amending it by title; decretos legislativos after 1626 and laws of 2026 could not be enumerated from here, so later amendments may be missing.",
        "Ley 29733 original text: ANPD/MINJUS copy on gob.pe (2023), which prints each replaced text before the D.Leg. 1353 text; every unit not amended was checked word for word against the current Editora Perú edition and the 2016 MINSA copy.",
        "Ley 29733 in force from 4 July 2011 (published 3 July; Const. art. 109) for Título II, art. 32 and the 1st-4th, 9th and 10th final provisions; the rest 30 business days after the reglamento (D.S. 003-2013-JUS, El Peruano 22 March 2013): counted from 25 March 2013, skipping 28-29 March (Holy Week) and 1 May, that is 8 May 2013. Recorded as a no-words commit crediting D.S. 003-2013-JUS on those units.",
        "D.Leg. 1353's changes to Ley 29733 (arts. 2, 3, 12, 14, 15, 18, 20-22, 25, 27 and others listed in the notes, plus the Título IV heading) took effect on 16 September 2017, the day after D.S. 019-2017-JUS (El Peruano, 15 September 2017), as its second final provision requires; the fe de erratas of 12 January 2017 (art. 15 numbering) predates that day and is included.",
        "Ley 29733 has no undécima disposición complementaria final in any source checked; the numbering jumps from décima to duodécima.",
    ]
    part = {
        "laws": laws,
        "acts": acts,
        "sources": [
            {"name": "Editora Perú, Normas Legales Actualizadas: Código Civil (FAOLEX copy)", "url": SRC["cc_nla"], "retrieved": "2026-10-28",
             "requests": 1, "licence": "Official text (Peruvian legal norms are not subject to copyright, D.Leg. 822 art. 9)", "notes": "PDF, two columns; current to 15 Aug 2024"},
            {"name": "El Peruano, busquedas.elperuano.pe", "url": "https://busquedas.elperuano.pe", "retrieved": "2026-10-28", "requests": 1,
             "licence": "Official gazette", "notes": "D.Leg. 1626 as published"},
            {"name": "Congreso, Archivo Digital de la Legislación del Perú", "url": "https://www.leyes.congreso.gob.pe", "retrieved": "2026-10-28",
             "requests": 40, "licence": "Official", "notes": "Ley 32228 text; law index by number (discovery only)"},
            {"name": "Editora Perú NLA: Ley 29733 (Wayback raw captures)", "url": SRC["dp_nla_2026"], "retrieved": "2026-10-28", "requests": 3,
             "licence": "Official text", "notes": "captures 20260409192208 and 20260721055737; the live file is corrupted"},
            {"name": "ANPD (MINJUS) on gob.pe: Ley 29733", "url": SRC["dp_anpd"], "retrieved": "2026-10-28", "requests": 2,
             "licence": "Official", "notes": "original and amended texts"},
            {"name": "MINSA on gob.pe: Ley 29733 (2016)", "url": SRC["dp_minsa"], "retrieved": "2026-10-28", "requests": 1,
             "licence": "Official", "notes": "cross-check only"},
        ],
        "decisions": decisions,
        "ai_use": ["codes part: none. A model wrote the parser; no model output is used as legal text."],
    }
    if report:
        print("\n".join(REPORT))
    tmp = OUT.with_suffix(".json.tmp")
    OUT.parent.mkdir(exist_ok=True)
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, OUT)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


def label_cc(k: str) -> str:
    if k.startswith("tp-"):
        return "Título Preliminar, art. " + [r for r, n in ROMAN.items() if n == int(k[3:])][0]
    m = re.fullmatch(r"art-(\d+)(?:-([a-z]))?", k)
    return "Art. %d%s" % (int(m.group(1)), "-" + m.group(2).upper() if m.group(2) else "")


def sort_cc(k: str):
    if k == "estructura":
        return (3, 0, "")
    if k.startswith("tp-"):
        return (0, int(k[3:]), "")
    m = re.fullmatch(r"art-(\d+)(?:-([a-z]))?", k)
    return (1, int(m.group(1)), m.group(2) or "")


if __name__ == "__main__":
    main()
