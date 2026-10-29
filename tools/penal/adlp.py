"""Laws that El Peruano's search index lacks (its index holds, for example, 91 of the ~180 laws of 2019).

For such a law the Congress's Archivo Digital de la Legislación del Perú (ADLP) holds a transcription of the text
published in El Peruano ("PUBLICADA EL … EN EL DIARIO OFICIAL EL PERUANO"), Texto_Consolidado/N-TXM.pdf, with a text
layer; Documentos/Leyes/N.pdf is the fallback (older ones are image scans and are not read: no OCR).

    python -X utf8 penal/adlp.py scan N [N ...]     discovery: which of these laws name the Código Penal
                                                    -> .tmp/adlp_scan.jsonl
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fetch  # noqa: E402
from elperuano import cp_hits  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)
TXM = 'https://www.leyes.congreso.gob.pe/Documentos/%s/ADLP/Texto_Consolidado/%s-TXM.pdf'
LEYES = 'https://www.leyes.congreso.gob.pe/Documentos/Leyes/%s.pdf'


def urls(n: int) -> list[str]:
    folders = ['2021_2026', '2016_2021'] if n >= 31200 else ['2016_2021', '2021_2026']
    if n >= 32700:
        folders = ['2026_2031'] + folders
    return [TXM % (f, n) for f in folders] + [LEYES % n]


def text_of(n: int) -> tuple[str | None, str]:
    """(url, text) of the first candidate that has a text layer."""
    for u in urls(n):
        p = fetch.cached(u)
        if p is None:
            m = fetch.meta_for(u)
            if m.exists() and json.loads(m.read_text(encoding='utf-8')).get('status') == 404:
                continue
            p = fetch.get(u)
        if p is None:
            continue
        try:
            d = fitz.open(str(p))
            t = '\n'.join(pg.get_text() for pg in d)
        except Exception:      # noqa: BLE001
            continue
        if len(t.strip()) > 200:
            return u, t
    return None, ''


def scan(nums):
    out = HERE / '.tmp' / 'adlp_scan.jsonl'
    done = set()
    if out.exists():
        done = {json.loads(l)['n'] for l in out.read_text(encoding='utf-8').splitlines()}
    for n in nums:
        if n in done:
            continue
        u, t = text_of(n)
        hits = cp_hits(t) if t else []
        m = re.search(r'PUBLICAD[AO] EL (\d+ DE \w+ DE \d{4})', t)
        rec = {'n': n, 'url': u, 'nhits': len(hits), 'hits': hits[:6], 'published': m.group(1) if m else None,
               'title': ' '.join(t.split())[:200]}
        with out.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print(n, u, len(hits), rec['published'], flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'scan':
        scan([int(x) for x in sys.argv[2:]])
