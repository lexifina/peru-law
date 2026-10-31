"""Código Procesal Constitucional part: corpus.d/85-procconst.json.

The act as enacted (Ley 31307, El Peruano 23 July 2021) and every law that changed it, each read from El Peruano's own
PDF extract of the norm (penal/lawtext.py cuts the norm's paragraphs). Changes are written by hand in laws.json as
compositions of each changed unit: lines of the unit before the law (["old", i], 0 = heading line) and paragraphs of
the law (["new", i]). The result is compared word for word with Editora Perú's Normas Legales Actualizadas
(idNorma=7) on each checkpoint day (strict: every word of the whole Code, in order).

    python -X utf8 procconst/parse_procconst.py          (env PC_DRY=1: no write)
"""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import fitz

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'penal'))
import lawtext  # noqa: E402
import nla  # noqa: E402

fitz.TOOLS.mupdf_display_errors(False)
CACHE = ROOT / '.cache'
PART = ROOT / 'corpus.d' / '85-procconst.json'
SLUG = 'codigo-procesal-constitucional'
ORD = ['PRIMERA', 'SEGUNDA', 'TERCERA', 'CUARTA', 'QUINTA', 'SEXTA', 'SÉPTIMA', 'OCTAVA', 'NOVENA', 'DÉCIMA']
ORD_ES = ['primera', 'segunda', 'tercera', 'cuarta', 'quinta', 'sexta', 'séptima', 'octava', 'novena', 'décima']
ROMAN = {'I': 1, 'V': 5, 'X': 10, 'L': 50}



def close_quote(line: str) -> str:
    """The closing quotation mark of an amending law's quoted wording is removed; a full stop printed after it ("...
    texto”.") is the quoted provision's own full stop and is kept, unless the wording already ends in punctuation."""
    m = re.search(r'[”"](\.?)$', line)
    if not m:
        return line
    body = line[:m.start()].rstrip()
    if m.group(1) and not re.search(r'[.;:,!?]$', body):
        body += '.'
    return body

def roman(s: str) -> int:
    n = 0
    for a, b in zip(s, s[1:] + ' '):
        v = ROMAN[a]
        n += -v if b != ' ' and ROMAN[b] > v else v
    return n


def cached(url: str) -> Path:
    p = CACHE / hashlib.sha256(url.encode('utf-8')).hexdigest()
    if not p.exists():
        raise SystemExit(f'not cached: {url}')
    return p


def law_paras(law: dict) -> tuple[list[str], str]:
    p = cached(law['pdf'])
    paras = lawtext.paragraphs(p, law['op'], law['heading'])
    return [clean(x) for x in paras], hashlib.sha256(p.read_bytes()).hexdigest()


def clean(s: str) -> str:
    # the text layer spells some í as a dotless i and a combining acute: the same letter
    s = s.replace('ı́', 'í').replace('[…]', '[...]')
    return ' '.join(s.split())


HEAD = re.compile(r'^Artículo (?P<n>[IVXL]+|\d+)(?:-(?P<s>[A-Z]))?\. ')
DISP = re.compile(r'^(?P<o>PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|SÉPTIMA|OCTAVA|NOVENA|DÉCIMA|ÚNICA)\. ')


def key_of(m) -> tuple[str, str]:
    n, s = m.group('n'), m.group('s')
    if re.fullmatch(r'[IVXL]+', n):
        return 'tp-%02d' % roman(n), f'Título Preliminar, art. {n}'
    return 'art-%03d%s' % (int(n), '-' + s.lower() if s else ''), f'Art. {n}' + (f'-{s}' if s else '')


def enacted_units(paras: list[str]) -> dict:
    """Units of Ley 31307 as published: Título Preliminar, articles and the complementary provisions."""
    units: dict = {}
    cur = None
    section = None          # None (articles), 'dcf', 'dct', 'dcd'
    start = next(i for i, p in enumerate(paras) if p.endswith('TÍTULO PRELIMINAR')) + 1
    for p in paras[start:]:
        if p == 'POR TANTO:':
            break
        if re.fullmatch(r'DISPOSICI[ÓO]N(ES)?', p):
            cur = None
            continue
        if p.startswith('COMPLEMENTARIAS FINALES'):
            section = 'dcf'
            continue
        if p.startswith('COMPLEMENTARIA TRANSITORIA'):
            section = 'dct'
            continue
        if p.startswith('DISPOSICIÓN COMPLEMENTARIA DEROGATORIA'):
            section, cur = 'dcd', None
            continue
        m = HEAD.match(p)
        if m and section is None:
            k, label = key_of(m)
            cur = k
            units[k] = {'label': label, 'kind': 'art', 'lines': [p]}
            continue
        m = DISP.match(p)
        if m and section:
            o = m.group('o')
            n = 1 if o == 'ÚNICA' else ORD.index(o) + 1
            name = {'dcf': 'final', 'dct': 'transitoria', 'dcd': 'derogatoria'}[section]
            cur = '%s-%02d' % (section, n)
            word = 'única' if o == 'ÚNICA' else ORD_ES[n - 1]
            units[cur] = {'label': f'Disposición complementaria {name} {word}', 'kind': 'provision', 'lines': [p]}
            continue
        if re.fullmatch(r'(TÍTULO|CAPÍTULO) [IVXL]+', p) or (p.upper() == p and not re.search(r'\d', p)):
            cur = None if section is None else cur     # a structure heading ends the article
            if section is None:
                continue
        if cur is None:
            raise SystemExit(f'paragraph outside a unit: {p[:80]}')
        units[cur]['lines'].append(p)
    return units


def as_unit(u: dict) -> dict:
    return {'label': u['label'], 'kind': u['kind'], 'text': '\n'.join(u['lines']) + '\n'}


def apply_law(law: dict, units: dict, paras: list[str]) -> list[str]:
    """Apply the hand compositions of one law; returns the changed keys."""
    changed = []
    for key, comp in law['compose'].items():
        old = units.get(key, {}).get('lines', [])
        lines = []
        for item in comp:
            kind, i = item[0], item[1]
            if kind == 'old':
                lines.append(old[i])
            elif kind == 'new':
                t = paras[i].strip('“”"')
                if len(item) > 2:           # ["new", i, "prefix"]: the paragraph from that text on
                    t = t[t.index(item[2]):]
                if len(item) > 3:           # ["new", i, "prefix", "until"]: up to (not including) that text
                    t = t[:t.index(item[3])]
                lines.append(t.strip().strip('“”"').strip())
            elif kind == 'oldrange':        # ["oldrange", a, b]: old lines a..b-1 (b null: to the end)
                lines += old[i:item[2]]
            else:
                raise SystemExit(f'{law["key"]} {key}: bad item {item}')
        if '[...]' in ''.join(lines):
            raise SystemExit(f'{law["key"]} {key}: an ellipsis left in the text')
        lines = [close_quote(l) if l.endswith(('”', '”.')) else l for l in lines]
        if key in units and units[key]['lines'] == lines:
            continue
        lab = law.get('labels', {}).get(key)
        units[key] = {'label': lab or units.get(key, {}).get('label') or key, 'kind': units.get(key, {}).get('kind', 'art'),
                      'lines': lines}
        changed.append(key)
    return changed


# ---------------------------------------------------------------- checkpoints against Editora Perú (idNorma=7)

def nla_words(path: Path) -> list[str]:
    runs = nla.stream(fitz.open(str(path)))
    text = ''.join(t for t, n in runs if not n)
    text = re.sub(r'\xad\n', '', text)
    start = text.index('TÍTULO PRELIMINAR\nArtículo I.')
    end = text.index('POR TANTO', start)
    keep = []
    for line in text[start:end].split('\n'):
        s = line.strip()
        if not s:
            continue
        if s.upper() == s and not re.search(r'[a-záéíóúñ]', s):     # structure headings (TÍTULO, CAPÍTULO, names)
            if not re.match(r'^\d|^[a-z]\)', s):
                continue
        keep.append(s)
    return nla.words(' '.join(keep))


def our_words(units: dict) -> list[str]:
    def order(k):
        sec = {'tp': 0, 'art': 1, 'dcf': 2, 'dct': 3, 'dcd': 4}[k.split('-')[0]]
        return (sec, k)
    text = []
    for k in sorted(units, key=order):
        for l in units[k]['lines']:
            if l.upper() == l and not re.search(r'[a-záéíóúñ]', l) and not re.match(r'^\d|^[a-z]\)', l):
                continue
            text.append(l)
    return nla.words(' '.join(text))


def checkpoint(units: dict, capture: str) -> list[str]:
    url = f'https://web.archive.org/web/{capture}id_/https://diariooficial.elperuano.pe/Normas/obtenerDocumento?idNorma=7'
    a, b = our_words(units), nla_words(cached(url))
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != 'equal':
            out.append('%s ours[%s] nla[%s] at ...%s' % (op, ' '.join(a[i1:i2][:15]), ' '.join(b[j1:j2][:15]),
                                                          ' '.join(a[max(0, i1 - 8):i1])))
    return out


def main():
    spec = json.loads((HERE / 'laws.json').read_text(encoding='utf-8'))
    base = spec['enacted']
    paras, sha = law_paras(base)
    units = enacted_units(paras)
    versions = [{'from': base['in_force'], 'source_url': base['pdf'], 'sha256': sha,
                 'units': {k: as_unit(units[k]) for k in sorted(units)},
                 'credits': {}, 'note': f'Ley 31307 as published in El Peruano on {base["published"]} ({base["pdf"]}).'}]
    laws = {base['key']: {k: base.get(k) for k in ('label', 'title', 'kind', 'enacted', 'published')} |
            {'url': base['pdf'], 'temporary_until': None, 'restores': None, 'note': None}}
    results = {}
    cps = sorted(spec['checkpoints'], key=lambda c: c['date'])
    for law in sorted(spec['laws'], key=lambda l: (l['in_force'], l['key'])):
        for c in cps:
            if c['id'] not in results and c['date'] < law['in_force']:
                results[c['id']] = checkpoint(units, c['capture'])
        lp, lsha = law_paras(law)
        before = {k: dict(v, lines=list(v['lines'])) for k, v in units.items()}
        ch = apply_law(law, units, lp)
        if not ch:
            raise SystemExit(f'{law["key"]}: no change')
        changes = {k: (as_unit(units[k]) if k in units else None) for k in sorted(ch)}
        versions.append({'from': law['in_force'], 'source_url': law['pdf'], 'sha256': lsha, 'changes': changes,
                         'credits': {k: [law['key']] for k in sorted(ch)},
                         'note': f'Wording of {law["label"]} from its El Peruano text ({law["pdf"]}).'})
        laws[law['key']] = {k: law.get(k) for k in ('label', 'title', 'kind', 'enacted', 'published')} | \
            {'url': law['pdf'], 'temporary_until': None, 'restores': None, 'note': None}
        print(law['key'], law['in_force'], 'changed', ch)
        del before
    for c in cps:
        if c['id'] not in results:
            results[c['id']] = checkpoint(units, c['capture'])
    decisions = list(spec['decisions'])
    for law in [base] + sorted(spec['laws'], key=lambda l: l['in_force']):
        if law.get('vigencia'):
            decisions.append(f'Código Procesal Constitucional: {law["label"]} is in force on {law["in_force"]}: {law["vigencia"]}')
        if law.get('hand'):
            decisions.append(f'Código Procesal Constitucional: {law["label"]}: {law["hand"]}')
    bad = 0
    for c in cps:
        r = results[c['id']]
        expl = spec.get('explained', {}).get(c['id'], [])
        print('checkpoint %s (%s): %d differences' % (c['id'], c['date'], len(r)))
        for x in r:
            print('   ', x[:300])
        if len(r) > len(expl):
            bad += 1
        decisions.append(
            f'Código Procesal Constitucional checkpoint {c["id"]}: the whole rebuilt text on {c["date"]} equals Editora '
            f'Perú\'s Normas Legales Actualizadas (Internet Archive capture {c["capture"]}) word for word.' if not r else
            f'Código Procesal Constitucional checkpoint {c["id"]}: the rebuilt text on {c["date"]} compared word for word '
            f'with Editora Perú\'s Normas Legales Actualizadas (capture {c["capture"]}): {len(r)} differences: '
            + ' '.join(expl))
    part = {
        'laws': {k: laws[k] for k in sorted(laws)},
        'acts': [{'slug': SLUG, 'short': 'CPConst', 'title': 'Nuevo Código Procesal Constitucional (Ley 31307)',
                  'url': base['pdf'], 'first_law': base['key'], 'earlier_laws': [], 'versions': versions}],
        'sources': spec['sources'],
        'decisions': decisions,
        'ai_use': spec['ai_use'],
    }
    if os.environ.get('PC_DRY'):
        print('dry run:', len(versions), 'versions')
        return
    if bad:
        raise SystemExit('unexplained checkpoint differences: part not written')
    tmp = PART.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, PART)
    print('wrote', PART, len(versions), 'versions', len(laws), 'laws')


if __name__ == '__main__':
    main()
