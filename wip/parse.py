"""Build corpus.json (1993 Constitution of Peru) from the cache only.

    python -X utf8 parse.py            write corpus.json (atomically) and print the checkpoint report

Method (see the decisions list below for every hand choice):
  * Base text: the Congreso de la República editions of May 2021 and December 2024 (same typesetting).
  * Backward: the May 2021 edition's footnotes give, for every reform up to Ley 31122, the text the
    provision had "antes de la reforma". Replaying them backwards from the 2021 body yields every
    earlier version down to the 1993 text. Where the 2021 notes give no earlier text, the 2012
    Congreso consolidation's notes (or its body) fill the gap; each such case is listed in GAPS.
  * Forward: reforms after May 2021 take their text from the December 2024 edition body, from the
    reform law itself (laws later struck down by the Tribunal Constitucional) or, for Ley 31988, from
    the December 2024 edition's notes, which quote the future text.
  * Checkpoints: every reconstructed state is compared word by word (typography-insensitive) with the
    Congreso editions of 2004, 2012, 2015, 2019 (two) and 2021, and exactly with 2021 and 2024.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import editions as E  # noqa: E402
import fetch  # noqa: E402

WB = "https://web.archive.org/web/"
ED = {
    "e04": (WB + "20040619190058id_/http://www.congreso.gob.pe/ntley/Imagenes/Constitu/Cons1993.pdf", "old", "2000-11-05"),  # captured 2004 but not updated after 1995
    "e12": (WB + "20120511002326id_/http://www.congreso.gob.pe/ntley/Imagenes/Constitu/Cons1993.pdf", "old", "2012-05-11"),
    "e15": (WB + "20160405125615id_/http://www.congreso.gob.pe/Docs/files/constitucionpolitica-27-04-2015.pdf", "old", "2015-04-27"),
    "e19a": (WB + "20190713150404id_/http://www.congreso.gob.pe/Docs/files/constitucion/constitucion-politica-06-02-19.pdf", "old", "2019-02-06"),
    "e19b": (WB + "20190703212915id_/http://www.congreso.gob.pe/Docs/files/constitucion/Constitucion-politica-08-04-19.pdf", "old", "2019-04-08"),
    "e21": (WB + "20210707230309id_/http://www.congreso.gob.pe/Docs/files/constitucion/constitucion-2021-01-07-2021.pdf", "footnote", "2021-05-31"),
    "e24": ("https://www3.congreso.gob.pe/Docs/files/constitucion/constitucion-12-2024.pdf", "star", "2024-12-31"),
}
ADLP = "https://www.leyes.congreso.gob.pe/Documentos/"
LEY_PDF = {  # reform laws whose text we read (ADLP, Archivo Digital de la Legislación del Perú)
    "ley-31280": ADLP + "2016_2021/ADLP/Texto_Consolidado/31280-TXM.pdf",
    "ley-31304": ADLP + "2016_2021/ADLP/Texto_Consolidado/31304-TXM.pdf",
    "ley-31305": ADLP + "2016_2021/ADLP/Texto_Consolidado/31305-TXM.pdf",
}
TC_URL = "https://tc.gob.pe/jurisprudencia/2021/00019-2021-AI.pdf"
DOCS_DATE = "2026-10-28"


def law_url(n: int) -> str:
    if n >= 31400:
        return ADLP + f"2021_2026/ADLP/Texto_Consolidado/{n}-TXM.pdf"
    if n >= 30558:
        return ADLP + f"2016_2021/ADLP/Texto_Consolidado/{n}-TXM.pdf"
    return ADLP + f"Leyes/{n}.pdf"


# Reform laws: (number, published in El Peruano, title as listed by the Congreso). In force the next
# day (Const. art. 109) unless IN_FORCE says otherwise. Source: "Reformas a la Constitución" list in
# the Dec 2024 edition and https://www3.congreso.gob.pe/diariodebates/leyesrefconstit/
REFORMS = [
    (26470, "1995-06-12", "Modifican la Constitución Política del Estado, en lo referido a las garantías constitucionales"),
    (26472, "1995-06-13", "Modifican la Constitución Política del Estado, en lo referido a la asignación de recursos del presupuesto del sector público"),
    (27365, "2000-11-05", "Ley de reforma constitucional que elimina la reelección presidencial inmediata y modifica la duración del mandato del presidente, vicepresidentes y congresistas de la República elegidos en las elecciones generales de 2000"),
    (27600, "2001-12-16", "Ley que suprime firma y establece proceso de reforma constitucional"),
    (27680, "2002-03-07", "Ley de reforma constitucional del Capítulo XIV del Título IV, sobre descentralización"),
    (28389, "2004-11-17", "Ley de reforma de los artículos 11, 103 y primera disposición final y transitoria de la Constitución Política del Perú"),
    (28390, "2004-11-17", "Ley de reforma de los artículos 74 y 107 de la Constitución Política del Perú"),
    (28480, "2005-03-30", "Ley de reforma de los artículos 31 y 34 de la Constitución Política del Perú"),
    (28484, "2005-04-05", "Ley de reforma de los artículos 87, 91, 92, 96 y 101 de la Constitución Política del Perú"),
    (28607, "2005-10-04", "Ley de reforma de los artículos 91, 191 y 194 de la Constitución Política del Perú"),
    (29401, "2009-09-08", "Ley de reforma de los artículos 80 y 81 de la Constitución Política del Perú"),
    (29402, "2009-09-08", "Ley de reforma del artículo 90 de la Constitución Política del Perú"),
    (30305, "2015-03-10", "Ley de reforma de los artículos 191, 194 y 203 de la Constitución Política del Perú sobre denominación y no reelección inmediata de autoridades de los gobiernos regionales y de los alcaldes"),
    (30558, "2017-05-09", "Ley de reforma del literal f del inciso 24 del artículo 2 de la Constitución Política del Perú"),
    (30588, "2017-06-22", "Ley de reforma constitucional que reconoce el derecho de acceso al agua como derecho constitucional"),
    (30650, "2017-08-20", "Ley de reforma del artículo 41 de la Constitución Política del Perú"),
    (30651, "2017-08-20", "Ley de reforma del artículo 203 de la Constitución Política del Perú, para otorgar legitimación activa al presidente del Poder Judicial en los procesos de inconstitucionalidad"),
    (30738, "2018-03-14", "Ley de reforma del artículo 52 de la Constitución Política del Perú"),
    (30904, "2019-01-10", "Ley de reforma constitucional sobre la conformación y funciones de la Junta Nacional de Justicia"),
    (30905, "2019-01-10", "Ley que modifica el artículo 35 de la Constitución Política del Perú para regular el financiamiento de organizaciones políticas"),
    (30906, "2019-01-10", "Ley de reforma constitucional que prohíbe la reelección inmediata de parlamentarios de la República"),
    (31043, "2020-09-15", "Ley de reforma constitucional que incorpora el artículo 34-A y el artículo 39-A sobre impedimentos para postular a cargos de elección popular o ejercer función pública"),
    (31097, "2020-12-29", "Ley de reforma del artículo 16 de la Constitución Política del Perú con el fin de fortalecer el sector educación"),
    (31118, "2021-02-06", "Ley de reforma constitucional que elimina la inmunidad parlamentaria"),
    (31122, "2021-02-10", "Ley de reforma constitucional que habilita el doble empleo o cargo público remunerado del personal médico especializado o asistencial de salud, en casos de emergencia sanitaria"),
    (31280, "2021-07-16", "Ley de reforma constitucional que establece el régimen de residencia temporal del expresidente de la República"),
    (31304, "2021-07-23", "Ley de reforma constitucional que refuerza la protección del patrimonio cultural de la nación"),
    (31305, "2021-07-23", "Ley de reforma constitucional que fortalece la lucha anticorrupción en el marco del levantamiento del secreto bancario y la reserva tributaria"),
    (31414, "2022-02-12", "Ley de reforma constitucional que refuerza la protección del patrimonio cultural de la nación"),
    (31507, "2022-07-03", "Ley de reforma constitucional que fortalece la lucha anticorrupción en el marco del levantamiento del secreto bancario y la reserva tributaria"),
    (31878, "2023-09-23", "Ley de reforma constitucional que promueve el uso de las tecnologías de la información y la comunicación, y reconoce el derecho de acceso a internet libre en todo el país"),
    (31988, "2024-03-20", "Ley de reforma constitucional que restablece la bicameralidad en el Congreso de la República"),
    (32135, "2024-10-15", "Ley de reforma constitucional que incorpora la Disposición Transitoria Especial Cuarta en la Constitución Política del Perú para autorizar excepcionalmente la elaboración y aprobación de reglamentos"),
    (32145, "2024-10-29", "Ley de reforma constitucional del artículo 40 de la Constitución Política del Perú para habilitar el doble empleo o cargo público remunerado al personal médico o asistencial de salud"),
    (32188, "2024-12-11", "Ley de reforma constitucional que modifica los artículos 7 y 23 de la Constitución Política del Perú para considerar el término «discapacidad»"),
    (32189, "2024-12-11", "Ley de reforma constitucional del subtítulo del capítulo VI del título III y del artículo 89 de la Constitución Política del Perú para el reconocimiento del pueblo afroperuano"),
    (32265, "2025-03-22", "Ley que deroga la Ley 27600 y restituye la firma del presidente Alberto Fujimori Fujimori en la Constitución Política del Perú de 1993"),
]
IN_FORCE = {
    # Ley 31988, Primera Disposición Complementaria Final: "Las reformas constitucionales comprendidas en
    # esta ley entran en vigor a partir de las próximas elecciones generales" -> general elections of
    # Sunday 12 April 2026 (Decreto Supremo 039-2025-PCM).
    "ley-31988": "2026-04-12",
}
NOTES = {
    "ley-27600": "Removed the signature of Alberto Fujimori from the text of the Constitution and set the procedure for a new constitution; no provision's wording changed.",
    "ley-32265": "Repealed Ley 27600 and restored the signature of Alberto Fujimori to the Constitution of 1993; no provision's wording changed.",
    "ley-29402": "Its Disposición Transitoria Única says the reform \"entra en vigencia para el proceso electoral del año 2011\"; the text is dated from the day after publication.",
    "ley-31043": "Published on 15 September 2020 as Ley 31042; the number was corrected to 31043 by a fe de erratas published on 20 September 2020.",
}
TC_KEY = "tc-00019-2021-pi"


def plus1(d: str) -> str:
    return (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()


def in_force(key: str, pub: str) -> str:
    return IN_FORCE.get(key, plus1(pub))


LAW_DATE = {f"ley-{n}": in_force(f"ley-{n}", p) for n, p, _ in REFORMS}
LAW_DATE[TC_KEY] = "2021-11-27"  # STC 918/2021 published 26 Nov 2021; rige desde el día siguiente

# ----------------------------------------------------------------------------------------------
# Backward replay from the May 2021 edition. note id -> (unit, law, scope)
#   whole     the note quotes the whole earlier provision
#   new       the provision did not exist before the law
#   para_add  the marked paragraph did not exist before the law
#   marker    the marked paragraph is replaced by the quoted paragraph(s)
#   item:X    the item starting "X." up to the marked paragraph is replaced by the quoted text
NOTES21 = {
    "2": ("art-002", "ley-30558", "item:f"),
    "3": ("art-007-a", "ley-30588", "new"),
    "4": ("art-011", "ley-28389", "para_add"),
    "5": ("art-016", "ley-31097", "marker"),
    "6": ("art-031", "ley-28480", "whole"),
    "7": ("art-034", "ley-28480", "whole"),
    "8": ("art-034-a", "ley-31043", "new"),
    "9": ("art-035", "ley-30905", "whole"),
    "10": ("art-039-a", "ley-31043", "new"),
    "11": ("art-040", "ley-31122", "gap:e12-body"),
    "12": ("art-041", "ley-30650", "marker"),
    "13": ("art-052", "ley-30738", "marker"),
    "14": ("art-074", "ley-28390", "whole"),
    "15": ("art-077", "ley-26472", "whole"),
    "16": ("art-080", "ley-29401", "whole"),
    "17": ("art-081", "ley-29401", "whole"),
    "18": ("art-087", "ley-28484", "whole"),
    "19": ("art-090", "ley-29402", "whole"),
    "20": ("art-090-a", "ley-30906", "new"),
    "21": ("art-091", "ley-28607", "whole"),
    "22": ("art-092", "ley-28484", "marker"),
    "23": ("art-093", "ley-31118", "whole"),
    "24": ("art-096", "ley-28484", "marker"),
    "25": ("art-101", "ley-28484", "item:2"),
    "26": ("art-103", "ley-28389", "whole"),
    "27": ("art-107", "ley-28390", "whole"),
    "28": ("art-112", "ley-27365", "whole"),
    "30": ("art-154", "ley-30904", "whole"),
    "31": ("art-155", "ley-30904", "whole"),
    "32": ("art-156", "ley-30904", "whole"),
    "34": ("art-191", "ley-30305", "whole"),
    "35": ("art-194", "ley-30305", "whole"),
    "36": ("art-200", "ley-26470", "item:2"),
    "37": ("art-200", "ley-26470", "item:3"),
    "38": ("art-203", "ley-30651", "whole"),
    "39": ("dft-01", "ley-28389", "whole"),
    "40": ("dte-01", "ley-27365", "new"),
    "41": ("dte-02", "ley-27365", "new"),
    "42": ("dte-03", "ley-29402", "new"),
}
# Earlier steps the 2021 notes do not quote; their text comes from the 2012 Congreso consolidation.
#   unit -> list of (law, source) applied after the 2021-note step, newest first
GAPS = {
    "art-091": [("ley-28484", "e12-note:28484-num3")],   # 2021 note 21 only names Ley 28484 (numeral 3)
    "art-191": [("ley-28607", "e12-note:28607"), ("ley-27680", "e12-chapter")],
    "art-194": [("ley-28607", "e12-note:28607"), ("ley-27680", "e12-chapter")],
    "art-203": [("ley-30305", "e12-body-item:6")],       # 2021 note 38 only names Ley 30305 (numeral 6)
}
CHAPTER_XIV = [f"art-{n:03d}" for n in range(188, 200)]  # replaced as a whole by Ley 27680
for _u in CHAPTER_XIV:
    GAPS.setdefault(_u, [("ley-27680", "e12-chapter")])

# The Dec 2024 edition is the base for every provision whose words it shares with May 2021, except:
E24_ERRATA = {
    "art-091": "The December 2024 edition prints numeral 3 of Article 91 twice (as numerals 3 and 4) and renumbers the rest 5 and 6; no reform did this, so the May 2021 text is kept.",
}


def strip_heading(paras: list[str]) -> list[str]:
    """Drop the provision heading from quoted text: 'Artículo 34. ...', 'Primera. ...', '(...)' paragraphs,
    and title lines that precede the 'Artículo' paragraph."""
    out = list(paras)
    while out and not E.ART.match(out[0]) and len(out) > 1 and E.ART.match(out[1]):
        out.pop(0)  # e.g. "Requisitos para ser miembro del Consejo Nacional de la Magistratura"
    if out:
        m = E.ART.match(out[0]) or E.DISP.match(out[0])
        if m:
            rest = out[0][m.end():].strip()
            if rest in ("(...)", "(…)", "[...]", "[…]", ""):
                out.pop(0)
            else:
                out[0] = rest
    return [p for p in out if p not in ("(...)", "(…)")]


def item_start(paras: list[str], label: str, upto: int) -> int:
    for i in range(min(upto, len(paras) - 1), -1, -1):
        if re.match(rf"^{re.escape(label)}\.\s", paras[i]):
            return i
    raise SystemExit(f"item {label}. not found")


def item_block(paras: list[str], label: str) -> tuple[int, int]:
    """[i, j) of the item starting 'label.' and its sub-paragraphs (up to the next item)."""
    i = next(k for k, p in enumerate(paras) if re.match(rf"^{re.escape(label)}\.\s", p))
    j = i + 1
    while j < len(paras) and not E.ITEM.match(paras[j]):
        j += 1
    return i, j


def split_chapter(paras: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    cur = None
    for p in paras:
        m = E.ART.match(p)
        if m and p.startswith("Artículo"):
            cur = E.unit_key(m.group(1), m.group(2))
            out[cur] = [p[m.end():].strip()]
        elif cur:
            out[cur].append(p)
    return out


def main() -> int:
    ed = {k: E.Edition(u, st) for k, (u, st, _) in ED.items()}
    e21, e24, e12 = ed["e21"], ed["e24"], ed["e12"]
    decisions: list[str] = []
    problems: list[str] = []

    # --- 2012 sources for the gaps ------------------------------------------------------------
    def e12_note(pattern: str) -> list[str]:
        return E.quoted(e12.note_paras(e12.find_note(pattern)))

    chap = split_chapter(e12_note(r"Capítulo modificado por Ley N. ?27680"))
    if sorted(chap) != CHAPTER_XIV:
        raise SystemExit(f"chapter XIV note: {sorted(chap)}")
    gap_src = {
        "e12-note:28484-num3": e12_note(r"Numeral modificado por Ley N. ?28484.*este numeral.*“3\."),
        "e12-chapter": chap,
    }
    for u in ("art-191", "art-194"):
        gap_src[f"e12-note:28607:{u}"] = strip_heading(e12_note(
            r"Artículo modificado por Ley N. ?28607.*“Artículo " + str(int(u[4:])) + r"\b"))

    # --- backward replay ----------------------------------------------------------------------
    state = {k: list(v["paras"]) for k, v in e21.units.items()}
    events: dict[str, list[tuple[str, list[str] | None]]] = {}  # unit -> [(law, after)] newest first
    marks = {nid: (u, i) for u, v in e21.units.items() for nid, i in v["marks"]}
    for nid, (unit, law, scope) in sorted(NOTES21.items(), key=lambda t: -int(t[0])):
        u_marked, mi = marks[nid]
        if u_marked != unit:
            raise SystemExit(f"note {nid} sits in {u_marked}, table says {unit}")
        cur = state[unit]
        q = strip_heading(E.quoted(e21.note_paras(nid), past_y=(nid == "21")))
        if scope == "new":
            before = None
        elif scope == "whole":
            before = q
        elif scope == "para_add":
            before = cur[:mi] + cur[mi + 1:]
        elif scope == "marker":
            before = cur[:mi] + q + cur[mi + 1:]
        elif scope.startswith("item:"):
            i = item_start(cur, scope[5:], mi)
            before = cur[:i] + q + cur[mi + 1:]
        elif scope == "gap:e12-body":
            before = list(e12.units[unit]["paras"])
        else:
            raise SystemExit(scope)
        if scope != "new" and not before:
            raise SystemExit(f"note {nid}: empty earlier text")
        events.setdefault(unit, []).append((law, cur))
        state[unit] = before
    for unit, steps in GAPS.items():
        for law, src in steps:
            cur = state[unit]
            if src == "e12-note:28484-num3":
                i, j = item_block(cur, "3")
                before = cur[:i] + gap_src[src] + cur[j:]
            elif src == "e12-note:28607":
                before = gap_src[f"e12-note:28607:{unit}"]
            elif src == "e12-chapter":
                before = gap_src["e12-chapter"][unit]
            elif src == "e12-body-item:6":
                i, j = item_block(cur, "6")
                oi, oj = item_block(e12.units[unit]["paras"], "6")
                before = cur[:i] + e12.units[unit]["paras"][oi:oj] + cur[j:]
            else:
                raise SystemExit(src)
            events.setdefault(unit, []).append((law, cur))
            state[unit] = before
    original = state  # the 1993 text (None for provisions added later)

    # --- timelines ----------------------------------------------------------------------------
    T: dict[str, list[tuple[str, str | None, list[str] | None]]] = {}
    for unit in e21.order:
        T[unit] = [("1993-12-31", None, original.get(unit))]
        for law, after in reversed(events.get(unit, [])):
            T[unit].append((LAW_DATE[law], law, after))
    for unit, tl in T.items():
        dates = [d for d, _, _ in tl]
        if dates != sorted(dates):
            raise SystemExit(f"{unit}: events out of order {dates}")

    # The 2021 state of each provision takes the Dec 2024 wording when the words are the same.
    def p24(u: str) -> list[str]:
        return list(e24.units[u]["paras"])

    for unit in e21.order:
        if unit in E24_ERRATA:
            continue
        if unit in e24.units and E.words(T[unit][-1][2] or []) == E.words(p24(unit)):
            d, law, _ = T[unit][-1]
            T[unit][-1] = (d, law, p24(unit))

    # Ley 30904's renaming ("Consejo Nacional de la Magistratura" -> "Junta Nacional de Justicia",
    # Única Disposición Complementaria Final) appears in Article 39 of the Dec 2024 edition only.
    T["art-039"].append((LAW_DATE["ley-30904"], "ley-30904", p24("art-039")))

    def law_text(key: str) -> list[str]:
        url = LEY_PDF[key]
        rows = [r for r in E.rows_of(url)]
        paras = E.paragraphs(rows, 14.0, short=True)
        out = []
        for p in E.quoted(paras):  # "[…]" marks omitted parts; the ADLP text layer shows it as "[?]"
            p = re.sub(r"^\[(\?|…|\.\.\.)\]\s*", "", p)
            if p:
                out.append(p)
        return out

    # 31280 / 31304 / 31305 (struck down by the TC) -- text from the laws themselves
    t31280 = strip_heading(law_text("ley-31280"))
    t31304 = strip_heading(law_text("ley-31304"))
    q31305 = law_text("ley-31305")  # "Artículo 2.- Toda persona tiene derecho:" "[...]" "5. ..." ...
    i5 = next(k for k, p in enumerate(q31305) if p.startswith("5. A solicitar"))
    n5_31305 = q31305[i5:]
    a2 = T["art-002"][-1][2]
    i, j = item_block(a2, "5")
    sub = j
    while sub < len(a2) and not re.match(r"^6\.\s", a2[sub]):
        sub += 1
    a2_31305 = a2[:i] + n5_31305 + a2[sub:]
    s24 = p24("art-002")
    k5 = next(k for k, p in enumerate(s24) if p.startswith("5. A solicitar"))
    k6 = next(k for k, p in enumerate(s24) if p.startswith("6. A que"))
    a2_31507 = a2[:i] + s24[k5:k6] + a2[sub:]
    pre = {u: T[u][-1][2] for u in ("art-112", "art-021", "art-002")}
    T["art-112"].append((LAW_DATE["ley-31280"], "ley-31280", t31280))
    T["art-021"].append((LAW_DATE["ley-31304"], "ley-31304", t31304))
    T["art-002"].append((LAW_DATE["ley-31305"], "ley-31305", a2_31305))
    for u in ("art-112", "art-021", "art-002"):
        T[u].append((LAW_DATE[TC_KEY], TC_KEY, pre[u]))
    T["art-021"].append((LAW_DATE["ley-31414"], "ley-31414", p24("art-021")))
    T["art-002"].append((LAW_DATE["ley-31507"], "ley-31507", a2_31507))
    T["art-002"].append((LAW_DATE["ley-31878"], "ley-31878", s24))
    T["art-014-a"] = [("1993-12-31", None, None), (LAW_DATE["ley-31878"], "ley-31878", p24("art-014-a"))]
    T["dte-04"] = [("1993-12-31", None, None), (LAW_DATE["ley-32135"], "ley-32135", p24("dte-04"))]
    T["art-040"].append((LAW_DATE["ley-32145"], "ley-32145", p24("art-040")))
    for u in ("art-007", "art-023"):
        T[u].append((LAW_DATE["ley-32188"], "ley-32188", p24(u)))
    T["art-089"].append((LAW_DATE["ley-32189"], "ley-32189", p24("art-089")))

    # --- Ley 31988 (in force at the 2026 general elections), from the 2024 edition's notes ------
    d31988 = LAW_DATE["ley-31988"]
    marks24 = {nid: (u, i) for u, v in e24.units.items() for nid, i in v["marks"]}
    post: dict[str, list[str] | None] = {}
    for nid in sorted(e24.notes, key=lambda s: int(s[1:])):
        unit, mi = marks24[nid]
        head = e24.notes[nid].text()
        if "31988" not in head:
            problems.append(f"2024 note {nid} in {unit} is not about Ley 31988: {head[:80]}")
            continue
        cur = post.get(unit, T[unit][-1][2])
        paras = e24.note_paras(nid)
        q = E.quoted(paras)
        if re.match(r"Artículo derogado", head):
            post[unit] = None
            continue
        # a note may also carry new articles (102-A, 102-B): split the quotation at "Artículo N."
        chunks: list[tuple[str | None, list[str]]] = [(None, [])]
        for p in q:
            m = E.ART.match(p)
            if m and p.startswith("Artículo") and chunks[0][1]:
                chunks.append((E.unit_key(m.group(1), m.group(2)), [p]))
            else:
                chunks[-1][1].append(p)
        own = chunks[0][1]
        for extra, ps in chunks[1:]:
            post[extra] = strip_heading(ps)
        kind = re.match(r"(Artículo|Párrafos? [\d, y]+|Párrafo|Numeral|El primer párrafo y los numerales [\d y]+)", head)
        kind = kind.group(1) if kind else ""
        if kind == "Artículo":
            post[unit] = strip_heading(own)
        elif kind == "Párrafo":
            post[unit] = cur[:mi] + own + cur[mi + 1:]
        elif kind == "Numeral":
            lab = re.match(r"^(\d+)\.", own[0]).group(1)
            i = item_start(cur, lab, mi)
            post[unit] = cur[:i] + own + cur[mi + 1:]
        elif kind.startswith("Párrafos") or kind.startswith("El primer párrafo"):
            post[unit] = strip_heading(own) + cur[mi + 1:]
        else:
            raise SystemExit(f"2024 note {nid}: unknown scope {head[:60]!r}")
    for unit, paras in post.items():
        T.setdefault(unit, [("1993-12-31", None, None)])
        T[unit].append((d31988, "ley-31988", paras))

    # --- paragraph harmonisation --------------------------------------------------------------
    # Editions disagree on some paragraph breaks after a full stop or colon. Split wherever either
    # modern edition splits, so that no version shows a break the next one lacks.
    pairs: set[tuple[str, str]] = set()
    for e in (e21, e24):
        for v in e.units.values():
            ps = v["paras"]
            for a, b in zip(ps, ps[1:]):
                if re.search(r"[.:]$", a) and len(a) >= 30 and len(b) >= 15:
                    pairs.add((a[-30:], b[:15]))

    def harmonise(ps: list[str] | None) -> list[str] | None:
        if ps is None:
            return None
        out = []
        for p in ps:
            changed = True
            while changed:
                changed = False
                for a, b in pairs:
                    k = p.find(a + " " + b)
                    if k > 0:
                        out.append(p[:k + len(a)])
                        p = p[k + len(a) + 1:]
                        changed = True
                        break
            out.append(p)
        return out

    for unit in T:
        T[unit] = [(d, law, harmonise(ps)) for d, law, ps in T[unit]]

    # --- checkpoints --------------------------------------------------------------------------
    def state_at(day: str) -> dict[str, list[str]]:
        out = {}
        for unit, tl in T.items():
            cur = None
            for d, _, ps in tl:
                if d <= day:
                    cur = ps
            if cur is not None:
                out[unit] = cur
        return out

    report: list[str] = []
    for k, (url, st, asof) in ED.items():
        s = state_at(asof)
        e = ed[k]
        miss = []
        for unit in sorted(set(s) | set(e.units)):
            if unit == "preambulo" and st == "old":
                continue  # the old editions set the preamble in bold capitals
            a = E.words(s.get(unit, []))
            b = E.words(e.units[unit]["paras"]) if unit in e.units else ""
            if a != b:
                miss.append(unit)
                if os.environ.get("PE_DIFF"):
                    import difflib
                    x, y = a.split(), b.split()
                    for o in difflib.SequenceMatcher(None, x, y, autojunk=False).get_opcodes():
                        if o[0] != "equal":
                            print(f"  {k} {unit} ours: {' '.join(x[max(0, o[1] - 4):o[2] + 3])!r}"
                                  f"  edition: {' '.join(y[max(0, o[3] - 4):o[4] + 3])!r}")
        exact = ""
        if k in ("e21", "e24"):
            ex = [u for u in e.units if harmonise(e.units[u]["paras"]) != s.get(u)]
            exact = f"; not identical: {', '.join(ex) or 'none'}"
        report.append(f"{k} ({asof}): {len(e.units)} provisions, word mismatches: {', '.join(miss) or 'none'}{exact}")

    # --- corpus -------------------------------------------------------------------------------
    order = list(e21.order)
    for u in ("art-014-a", "dte-04", "art-102-a", "art-102-b"):
        if u in T and u not in order:
            order.append(u)
    order.sort(key=sort_key)
    labels = {u: v["label"] for e in (e21, e24) for u, v in e.units.items()}
    labels.setdefault("art-102-a", "Artículo 102-A")
    labels.setdefault("art-102-b", "Artículo 102-B")

    dates = sorted({d for tl in T.values() for d, _, _ in tl})
    versions = []
    prev: dict[str, str] = {}
    src24 = ED["e24"][0]
    for day in dates:
        s = state_at(day)
        units = {}
        for u in order:
            if u in s:
                units[u] = {"label": labels[u], "kind": kind_of(u),
                            "text": f"# {labels[u]}\n" + "".join(p + "\n" for p in s[u])}
        credits: dict[str, list[str]] = {}
        for u in order:
            for d, law, _ in T.get(u, []):
                if d == day and law:
                    credits.setdefault(u, []).append(law)
        changed = {u for u in set(units) | set(prev) if units.get(u, {}).get("text") != prev.get(u)}
        for u in changed - set(credits):
            if day != dates[0]:
                problems.append(f"{day}: {u} changed without a credit")
        if day == "2025-03-23":
            credits.setdefault("preambulo", []).append("ley-32265")
        src = source_for(day)
        versions.append({"from": day, "source_url": src, "sha256": sha_of(src),
                         "units": units, "credits": {u: credits[u] for u in sorted(credits)} if day != dates[0] else {}})
        prev = {u: v["text"] for u, v in units.items()}
    # Ley 27600 and Ley 32265 change no words; they get a commit of their own (Words-changed: no).
    for key, day in (("ley-27600", LAW_DATE["ley-27600"]), ("ley-32265", LAW_DATE["ley-32265"])):
        if day not in dates:
            base = max(v for v in versions if v["from"] < day)["from"] if False else None
            last = [v for v in versions if v["from"] < day][-1]
            versions.append({"from": day, "source_url": src24, "sha256": sha_of(src24),
                             "units": last["units"], "credits": {"preambulo": [key]}})
    versions.sort(key=lambda v: v["from"])

    laws = {"constitucion-1993": {
        "label": "Constitución Política del Perú 1993", "title": "Constitución Política del Perú",
        "kind": "law", "enacted": "1993-12-29", "published": "1993-12-30",
        "url": "https://www.leyes.congreso.gob.pe/Documentos/constituciones_ordenado/CONSTIT_1993/CONST_1993_PUBL_PERUANO.pdf",
        "temporary_until": None, "restores": None,
        "note": "Approved by the Congreso Constituyente Democrático, ratified by referendum on 31 October 1993, promulgated on 29 December 1993 and published in El Peruano on 30 December 1993."}}
    for n, pub, title in REFORMS:
        key = f"ley-{n}"
        laws[key] = {"label": f"Ley {n}", "title": title, "kind": "law", "enacted": None, "published": pub,
                     "url": law_url(n), "temporary_until": None, "restores": None, "note": NOTES.get(key)}
    laws[TC_KEY] = {"label": "STC 918/2021 (Exp. 00019-2021-PI/TC y acumulados)",
                    "title": "Sentencia del Tribunal Constitucional, caso del desdoblamiento de las legislaturas ordinarias: declara la inconstitucionalidad por consecuencia de las leyes de reforma constitucional 31280, 31304 y 31305",
                    "kind": "court", "enacted": "2021-11-11", "published": "2021-11-26", "url": TC_URL,
                    "temporary_until": None, "restores": None, "note": None}
    used = {law for v in versions for ls in v["credits"].values() for law in ls}
    for k in list(laws):
        if k not in used and k != "constitucion-1993":
            problems.append(f"law {k} is never credited")

    corpus = {
        "country": {
            "code": "PE", "name": "Peru", "slug": "peru", "lang": "es", "tz": "America/Lima",
            "future_branch": "futuro",
            "publisher": {"name": "Congreso de la República del Perú", "email": "congreso@congreso.gob.pe.invalid"},
            "default_in_force_rule": {
                "text": "Constitución art. 109: la ley es obligatoria desde el día siguiente de su publicación en el diario oficial, salvo disposición contraria de la misma ley que posterga su vigencia en todo o en parte",
                "source": "https://www3.congreso.gob.pe/Docs/files/constitucion/constitucion-12-2024.pdf"},
            "licence_note": "Texto: Congreso de la República del Perú (ediciones oficiales de la Constitución Política del Perú) y Archivo Digital de la Legislación del Perú. Las normas legales no están protegidas por derecho de autor (Decreto Legislativo 822, art. 9).",
        },
        "sources": sources(),
        "laws": laws,
        "acts": [{
            "slug": "constitucion", "short": "CPP",
            "title": "Constitución Política del Perú de 1993",
            "url": "https://www3.congreso.gob.pe/Docs/files/constitucion/constitucion-12-2024.pdf",
            "first_law": "constitucion-1993", "earlier_laws": [],
            "versions": versions,
        }],
        "applies": [],
        "decisions": DECISIONS + [f"Checkpoint {r}" for r in report] + [v for v in E24_ERRATA.values()],
        "ai_use": ["none: no model wrote, translated or chose legal text. Parsing rules, the note table and the decisions were written by hand (by a coding agent) and are checked against the Congreso editions listed in the checkpoints."],
    }
    for r in report:
        print(r)
    for p in problems:
        print("PROBLEM:", p)
    print(f"{len(versions)} versions, {len(laws)} laws")
    tmp = HERE / "corpus.json.tmp"
    tmp.write_text(json.dumps(corpus, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, HERE / "corpus.json")
    return 0


def sort_key(u: str):
    if u == "preambulo":
        return (0, 0, "")
    m = re.match(r"art-(\d+)(?:-([a-z]))?$", u)
    if m:
        return (1, int(m.group(1)), m.group(2) or "")
    m = re.match(r"(dft|dte)-(\d+)$", u)
    if m:
        return (2 if m.group(1) == "dft" else 3, int(m.group(2)), "")
    return (4, 0, u)


def kind_of(u: str) -> str:
    if u.startswith("art-"):
        return "art"
    if u.startswith(("dft", "dte")):
        return "transitional"
    return "other"


def source_for(day: str) -> str:
    """The edition a version's text is read from: the 2021 edition (and its notes) up to May 2021,
    the 2024 edition after."""
    return ED["e21"][0] if day <= "2021-05-31" else ED["e24"][0]


_SHA: dict[str, str] = {}


def sha_of(url: str) -> str:
    if url not in _SHA:
        _SHA[url] = hashlib.sha256(fetch.cached(url).read_bytes()).hexdigest()
    return _SHA[url]


def sources() -> list[dict]:
    reqs: dict[str, int] = {}
    log = fetch.CACHE / "requests.jsonl"
    for line in log.read_text(encoding="utf-8").splitlines():
        u = json.loads(line)["url"]
        host = re.sub(r"^https?://", "", u).split("/")[0]
        reqs[host] = reqs.get(host, 0) + 1
    return [
        {"name": "Congreso de la República: ediciones de la Constitución Política del Perú (2021, 2024)",
         "url": "https://www3.congreso.gob.pe/Docs/files/constitucion/constitucion-12-2024.pdf",
         "retrieved": DOCS_DATE, "requests": reqs.get("www3.congreso.gob.pe", 0) + reqs.get("www.congreso.gob.pe", 0),
         "licence": "Official legal text; not protected by copyright (Decreto Legislativo 822, art. 9).",
         "notes": "The May 2021 edition is read from a Wayback Machine capture (20210707230309); the December 2024 edition live."},
        {"name": "Congreso de la República: consolidaciones anteriores (2004, 2012, 2015, 2019) via the Wayback Machine",
         "url": "https://web.archive.org/web/2012/http://www.congreso.gob.pe/ntley/Imagenes/Constitu/Cons1993.pdf",
         "retrieved": DOCS_DATE, "requests": reqs.get("web.archive.org", 0),
         "licence": "Official legal text.", "notes": "Capture timestamps are pinned in parse.py (ED)."},
        {"name": "Archivo Digital de la Legislación del Perú (ADLP), Congreso",
         "url": "https://www.leyes.congreso.gob.pe/", "retrieved": DOCS_DATE,
         "requests": reqs.get("www.leyes.congreso.gob.pe", 0) + reqs.get("leyes.congreso.gob.pe", 0),
         "licence": "Official legal text.", "notes": "Texts of Leyes 31280, 31304, 31305 and the reform laws; law index search."},
        {"name": "Tribunal Constitucional del Perú", "url": TC_URL, "retrieved": DOCS_DATE,
         "requests": reqs.get("tc.gob.pe", 0), "licence": "Official judgment.",
         "notes": "STC 918/2021; publication date 26 Nov 2021 per the Comisión de Constitución, Opinión Consultiva 5 (www3.congreso.gob.pe)."},
    ]


DECISIONS = [
    "SPIJ (spij.minjus.gob.pe), the Ministry of Justice's consolidated legislation, is excluded: it does not answer from here and full access is paid.",
    "Dates are in-force dates: the day after publication in El Peruano (Constitución art. 109) unless the law says otherwise.",
    "The 1993 text is in force from 31 December 1993, the day after its publication in El Peruano on 30 December 1993 (May 2021 edition, note 1).",
    "Ley 31988 (bicameral Congress) says its reforms 'entran en vigor a partir de las próximas elecciones generales'; we date them 12 April 2026, the general election day set by Decreto Supremo 039-2025-PCM. Its repeal of Article 90-A takes effect the same day, as the Dec 2024 edition notes.",
    "Ley 29402 (Article 90, 130 congresistas) is dated from the day after publication; its own transitional provision makes it apply to the 2011 elections (recorded in the law's note).",
    "Leyes 31280, 31304 and 31305 were declared unconstitutional by STC 918/2021 (published 26 November 2021, effective the next day, without retroactive effect); the ruling is a court law that restores the earlier text of Articles 112, 21 and 2.",
    "The texts of Leyes 31280, 31304 and 31305 come from the laws as published (ADLP), because no Congreso edition carries them.",
    "Every earlier text up to Ley 31122 comes from the May 2021 edition's footnotes ('Antes de la reforma, este artículo tuvo el siguiente texto'). Where those notes give none, the 2012 consolidation fills the gap: the original Chapter XIV (Arts. 188-199, replaced by Ley 27680), Arts. 191 and 194 between Leyes 27680 and 28607, numeral 3 of Art. 91 before Ley 28484, numeral 6 of Art. 203 before Ley 30305 and Art. 40 before Ley 31122 (the 2021 note names 'Ley 31222', a misprint for 31122, and quotes no earlier text).",
    "Texts are normalised once: degree signs after article numbers are dropped ('artículo 117°' -> 'artículo 117', as in the 2024 edition), and spaces, quotes and dashes are unified.",
    "Where the 2021 and 2024 editions break a paragraph differently after a full stop or colon, the break is kept in every version.",
    "Article 39 reads 'Junta Nacional de Justicia' in the Dec 2024 edition, applying the renaming in Ley 30904's Única Disposición Complementaria Final; the May 2021 edition still printed 'Consejo de la Magistratura'. We credit the change to Ley 30904 on its in-force date. Other articles that still name the 'Consejo Nacional de la Magistratura' in the 2024 edition are left as printed.",
    "Ley 31042's number was corrected to Ley 31043 by a fe de erratas (20 September 2020); the law is keyed ley-31043.",
    "Leyes 27600 (2001) and 32265 (2025) concern Alberto Fujimori's signature on the Constitution, not its provisions; each is a commit that changes no words, credited to the preamble.",
    "Ley 31878 changed numeral 4 of Article 2 as well as adding Article 14-A (Ley 31878, art. 1; the Congreso's list mentions only Article 14-A).",
    "Section headings (títulos, capítulos) are not yet tracked as a unit.",
    "No Congreso edition after December 2024 exists; the Congreso's list of reform laws (diariodebates/leyesrefconstit, read 28 October 2026) names none after Ley 32265.",
]


if __name__ == "__main__":
    sys.exit(main())
