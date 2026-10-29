"""El Peruano (Editora Perú) official texts of single norms, through busquedas.elperuano.pe.

The search site lists every norm published in a date range ("/?fechaIni=…&fechaFin=…&tipoPublicacion=NL&ci=ONLY",
20 per page, optionally "&tipoDispositivo=LEY" or "DECRETO LEGISLATIVO"). Each card carries the norm's operation
number (op, e.g. 2237339-3) and the official PDF extract "/api/archivo/file/<token>/*/<op>.PDF": El Peruano's own
typeset pages, with a text layer. Since about September 2026 the site's HTML replaces every non-ASCII byte with
U+FFFD, so the HTML is used only to find the PDF; the PDFs are intact.

    python -X utf8 penal/elperuano.py scan TIPO FROM TO     discovery: every norm of TIPO in [FROM, TO] (YYYYMMDD)
                                                            whose text names the Código Penal -> .tmp/scan.jsonl

Requests go through ../fetch.py (curl, sha256(URL) cache, 1 request per second per host, requests.jsonl). The scan
removes the cached PDFs of norms that never name the Code (their metadata and log lines stay).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

import fitz

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import fetch  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)
BASE = 'https://busquedas.elperuano.pe'
CARD = re.compile(r'href="/dispositivo/NL/([0-9]+-[0-9]+)"[^>]*><p class="text-xs text-muted-foreground">([^<]*)</p>'
                  r'<p class="text-xs font-medium text-muted-foreground">([^<]*)</p></a></div>'
                  r'<div class="p-3 pt-0"><a[^>]*>([^<]*)</a>')


PUB = 'NL'      # NL = Normas Legales; EX = Edición Extraordinaria (many decretos legislativos and some laws)


def listing_url(fi: str, ff: str, tipo: str | None, start: int) -> str:
    u = f'{BASE}/?fechaIni={fi}&fechaFin={ff}&tipoPublicacion={PUB}&ci=ONLY&start={start}'
    if tipo:
        u += '&tipoDispositivo=' + quote(tipo)
    return u


def get_retry(url: str, force: bool = False, tries: int = 5):
    """fetch.get, tried again after 10, 20, 40, 80 s: busquedas.elperuano.pe drops TLS handshakes in bursts."""
    import time
    for i in range(tries):
        p = fetch.get(url, force=force)
        if p is not None:
            return p
        if i + 1 < tries:
            time.sleep(10 * 2 ** i)
    return None


def listing(fi: str, ff: str, tipo: str | None = None, start: int = 0, force: bool = False):
    """(total, [{op, tipo, numero, sumilla, pdf}]) for one page."""
    p = get_retry(listing_url(fi, ff, tipo, start), force=force)
    if p is None:
        raise SystemExit(f'listing failed: {fi}-{ff} {tipo} {start}')
    s = p.read_text('utf8', 'replace')
    m = re.search(r'(\d+)<!-- --> <!-- -->dispositivos encontrados', s)
    total = int(m.group(1)) if m else 0
    out = []
    for op, t, num, sumilla in CARD.findall(s):
        f = re.search(r'/api/archivo/file/[A-Za-z0-9_-]+/\*/%s\.pdf' % re.escape(op), s, re.I)
        d = re.search(r'<span>%s</span><span>\w+ (\d\d)\.(\d\d)\.(\d{4})</span>' % re.escape(op), s)
        out.append({'op': op, 'tipo': t.strip(), 'numero': num.strip(), 'sumilla': sumilla.strip(),
                    'pdf': BASE + f.group(0) if f else None,
                    'date': '%s-%s-%s' % (d.group(3), d.group(2), d.group(1)) if d else None})
    return total, out


def all_items(fi, ff, tipo):
    total, items = listing(fi, ff, tipo, 0)
    start = len(items)
    while start < total and items:
        _, more = listing(fi, ff, tipo, start)
        if not more:
            break
        items += more
        start += len(more)
    return total, items


def items_split(fi: str, ff: str, tipo: str) -> list[dict]:
    """Every card of TIPO in [fi, ff]. Paging long result lists drops and repeats cards, so a range with more than
    one page is split in halves down to single days (and only a single day is paged)."""
    import datetime as dt
    total, items = listing(fi, ff, tipo, 0)
    if total <= len(items):
        return items
    a, b = dt.date(int(fi[:4]), int(fi[4:6]), int(fi[6:])), dt.date(int(ff[:4]), int(ff[4:6]), int(ff[6:]))
    if a == b:
        _, more = all_items(fi, ff, tipo)
        return more
    m = a + (b - a) // 2
    f = lambda d: d.strftime('%Y%m%d')  # noqa: E731
    return items_split(fi, f(m), tipo) + items_split(f(m + dt.timedelta(days=1)), ff, tipo)


def items_both(fi: str, ff: str, tipo: str) -> list[dict]:
    """items_split over the ordinary and the extraordinary editions, without repeated cards."""
    global PUB
    out, seen = [], set()
    for pub in ('NL', 'EX'):
        PUB = pub
        try:
            for it in items_split(fi, ff, tipo):
                if it['op'] not in seen:
                    seen.add(it['op'])
                    out.append(dict(it, pub=pub))
        finally:
            PUB = 'NL'
    return out


def pdf_text(path) -> str:
    d = fitz.open(str(path))
    return '\n'.join(pg.get_text() for pg in d)


CP = re.compile(r'C[óo]digo\s+Penal(?!\s+Militar)', re.I)
NOT_CP = re.compile(r'(?:Procesal|Procedimientos|Ejecuci[óo]n|Responsabilidad)\s+Penal|Penal\s+Militar', re.I)


def cp_hits(t: str) -> list[str]:
    flat = ' '.join(t.split())
    out = []
    for m in CP.finditer(flat):
        before = flat[max(0, m.start() - 25):m.start()]
        if re.search(r'(?:Procesal|Procedimientos|Ejecuci[óo]n|Responsabilidad)\s*$', before, re.I):
            continue
        out.append(flat[max(0, m.start() - 160):m.end() + 60])
    return out


def scan(tipo: str, fi: str, ff: str):
    out = HERE / '.tmp' / 'scan.jsonl'
    out.parent.mkdir(exist_ok=True)
    done = set()
    if out.exists():
        for l in out.read_text(encoding='utf-8').splitlines():
            r = json.loads(l)
            if not r.get('error'):          # failed fetches are tried again
                done.add(r['op'])
    items = items_both(fi, ff, tipo)
    print(tipo, fi, ff, 'listed', len(items), flush=True)
    for it in items:
        if it['op'] in done or not it['pdf']:
            continue
        p = get_retry(it['pdf'])
        rec = dict(it, range=[fi, ff])
        if p is None:
            rec['error'] = 'pdf failed'
        else:
            try:
                t = pdf_text(p)
            except Exception as e:      # noqa: BLE001
                t = ''
                rec['error'] = 'bad pdf: %s' % e
            hits = cp_hits(t)
            rec['hits'] = hits[:8]
            rec['nhits'] = len(hits)
            m = re.search(r'(Lunes|Martes|Mi[ée]rcoles|Jueves|Viernes|S[áa]bado|Domingo),?\s+(\d+)\s+de\s+(\w+)\s+de\s+(\d{4})', t)
            rec['fecha'] = ' '.join(m.groups()[1:]) if m else None
            if not hits:
                p.unlink()
        with out.open('a', encoding='utf-8') as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print(it['tipo'], it['numero'], it['op'], rec.get('nhits'), rec.get('fecha'), flush=True)


def erratas(fi: str, ff: str):
    """Discovery: every "FE DE ERRATAS" card in [fi, ff] -> .tmp/erratas.jsonl (no PDFs fetched)."""
    out = HERE / '.tmp' / 'erratas.jsonl'
    out.parent.mkdir(exist_ok=True)
    items = items_both(fi, ff, 'FE DE ERRATA')
    total = len(items)
    print('FE DE ERRATA', fi, ff, 'total', total, 'listed', len(items), flush=True)
    with out.open('a', encoding='utf-8') as fh:
        for it in items:
            fh.write(json.dumps(dict(it, range=[fi, ff]), ensure_ascii=False) + '\n')


def cards(tipo: str, fi: str, ff: str):
    """Discovery: every card of TIPO in [fi, ff] -> .tmp/cards.jsonl (no PDFs fetched); used to find reglamentos
    that set a law's in-force day."""
    out = HERE / '.tmp' / 'cards.jsonl'
    items = items_split(fi, ff, tipo)
    total = len(items)
    print(tipo, fi, ff, 'total', total, 'listed', len(items), flush=True)
    with out.open('a', encoding='utf-8') as fh:
        for it in items:
            fh.write(json.dumps(dict(it, range=[fi, ff]), ensure_ascii=False) + '\n')


if __name__ == '__main__':
    if sys.argv[1] == 'cards':
        cards(sys.argv[2], sys.argv[3], sys.argv[4])
    if sys.argv[1] == 'scan':
        scan(sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == 'erratas':
        erratas(sys.argv[2], sys.argv[3])
