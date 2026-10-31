"""Write a build_nla spec from a compact description (keeps the boilerplate in one place)."""
import json
from pathlib import Path

PUB = {"name": "Editora Perú (Normas Legales Actualizadas)", "email": "nla@editoraperu.com.pe.invalid"}
LIC = "Official texts (D.Leg. 822 art. 9)"


def law(key, label, title, kind='law', enacted=None, published=None, url=None):
    return {key: {"label": label, "title": title, "kind": kind, "enacted": enacted, "published": published, "url": url,
                  "temporary_until": None, "restores": None, "note": None}}


def write(name, *, part, slug, short, title, title_short, nid, nla_args, earlier, extra, base_cap, base_date, base_note,
          laws=(), checkpoints=(), explained=None, nla_desc, law_src=None, words, decisions=(), ai=None, **more):
    url = f"https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma={nid}"
    sources = [{"name": f"Editora Perú, Normas Legales Actualizadas: {title_short} (idNorma={nid}), {nla_desc}", "url": url,
                "retrieved": "2026-10-31", "requests": 1 + len(checkpoints), "licence": LIC + "; Editora Perú publication",
                "notes": "text layer"}]
    if law_src:
        sources.append({"name": f"Editora Perú, Diario Oficial El Peruano: {law_src}", "url": "https://busquedas.elperuano.pe/",
                        "retrieved": "2026-10-31", "requests": len(laws), "licence": LIC,
                        "notes": "named in each version's source_url with its sha256"})
    sources.append({"name": "Discovery only: El Peruano's search site listings of every ley, decreto legislativo and decreto de "
                            "urgencia, April 2021 - 31 October 2026; the Congreso's ADLP transcriptions; El Peruano's issue pages; "
                            "MEF copies of separatas", "url": "https://busquedas.elperuano.pe/", "retrieved": "2026-10-31",
                    "requests": 0, "licence": LIC, "notes": "used only to establish which laws change the law"})
    found = [l['label'] for l in laws]
    dec = list(decisions) + [
        f"{title_short}: amending norms after the first version were found by reading, for the words {words}, every ley, decreto "
        "legislativo and decreto de urgencia that El Peruano's search site lists from April 2021 to 31 October 2026, and the laws that site does "
        "not list in the Congreso's ADLP transcription, El Peruano's own pages or the MEF's copies of the separatas: "
        + (("only " + found[0] + " changes" if len(found) == 1 else ", ".join(found[:-1]) + " and " + found[-1] + " change")
           + " it; the others only cite it." if found else "none changes it; those found only cite it.")]
    spec = {"part": part, "slug": slug, "short": short, "title": title, "title_short": title_short, "url": url, "nla_id": nid,
            "nla_args": nla_args, "publisher": PUB, "earlier_laws": earlier, "extra_laws": extra,
            "base": {"capture": base_cap, "date": base_date, "note": base_note}, "laws": list(laws),
            "checkpoints": list(checkpoints), "explained": explained or {}, "sources": sources, "decisions": dec,
            "ai_use": [ai or f"{title_short}: none. The text is read from Editora Perú's and El Peruano's PDFs by script; the "
                       "placement of each amending norm's paragraphs, if any, was written by hand."]}
    spec.update(more)
    Path(f'more2/{name}.json').write_text(json.dumps(spec, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
