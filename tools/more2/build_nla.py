"""One act as a corpus.d part: the oldest version is Editora Perú's consolidated text (Normas Legales Actualizadas) of
a stated day; every later change is the amending norm's own wording, read from El Peruano's PDF of that norm
(penal/lawtext.py cuts its paragraphs) and placed by hand compositions in the act's spec; the result is compared word for
word, provision by provision, with Editora Perú's later consolidations.

    python -X utf8 more2/build_nla.py more2/<act>.json        (env DRY=1: no write; DIFF=1: print differences)

Spec: part, slug, short, title, url, nla_id, base {capture, date, note}, laws [{key,label,title,kind,enacted,
published,in_force,vigencia,op,pdf,heading,compose,labels,hand}], checkpoints [{id,date,capture}], explained
{checkpoint id: {unit key: reason}}, sources, decisions, ai_use, publisher.
Compositions: {unit key: [items]} with ["new", i(, from, until)], ["old", i], ["oldrange", a, b], or null to remove.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'penal'))
sys.path.insert(0, str(HERE))
import lawtext  # noqa: E402
import nladiff  # noqa: E402
import nlaunits  # noqa: E402

CACHE = ROOT / '.cache'


def cached(url: str) -> Path:
    p = CACHE / hashlib.sha256(url.encode('utf-8')).hexdigest()
    if not p.exists():
        raise SystemExit(f'not cached: {url}')
    return p


def clean(s: str) -> str:
    s = s.replace('ı́', 'í').replace('[…]', '[...]').replace('(…)', '(...)')
    return ' '.join(s.split())


def law_paras(law: dict) -> tuple[list[str], str]:
    p = cached(law['pdf'])
    paras = lawtext.paragraphs(p, law['op'], law['heading'])
    return [clean(x) for x in paras], hashlib.sha256(p.read_bytes()).hexdigest()


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


def as_unit(u: dict) -> dict:
    return {'label': u['label'], 'kind': u['kind'], 'text': '\n'.join(u['lines']) + '\n'}


def apply_law(law: dict, units: dict, paras: list[str], sub: bool = False):
    changed = []
    for key, comp in law['compose'].items():
        if comp is None:
            if key in units:
                del units[key]
                changed.append(key)
            continue
        old = units.get(key, {}).get('lines', [])
        lines = []
        for item in comp:
            kind, i = item[0], item[1]
            if kind == 'join':          # ["join", [item, item, ...]]: one paragraph the PDF splits (column break, inset box)
                parts = apply_law({'key': law['key'], 'compose': {'_': i}}, {'_': {'lines': old}}, paras, sub=True)
                lines.append(' '.join(parts))
                continue
            if kind == 'oldpart':       # ["oldpart", i, from, until]: part of an old line (a paragraph the law splits)
                t = old[i]
                if len(item) > 2 and item[2]:
                    t = t[t.index(item[2]):]
                if len(item) > 3 and item[3]:
                    t = t[:t.index(item[3])]
                lines.append(t.strip())
                continue
            if kind == 'old':
                lines.append(old[i])
            elif kind == 'new':
                t = paras[i].strip()
                if len(item) > 2 and item[2]:
                    t = t[t.index(item[2]):]
                if len(item) > 3 and item[3]:
                    t = t[:t.index(item[3])]
                lines.append(t.strip().strip('“”"').strip())
            elif kind == 'renum':       # ["renum", i, old, new, from, until]: a paragraph of a law that amends the act in
                t = paras[i].strip()    # another numbering: its leading article/numeral number `old` (only that) becomes
                if len(item) > 4 and item[4]:       # the act's number `new` (the numbering map; listed in decisions)
                    t = t[t.index(item[4]):]
                if len(item) > 5 and item[5]:
                    t = t[:t.index(item[5])]
                t = t.strip().strip('“”"').strip()
                if not t.startswith(item[2]):
                    raise SystemExit(f'{law["key"]} {key}: renum: {t[:40]!r} does not start with {item[2]!r}')
                lines.append(item[3] + t[len(item[2]):])
            elif kind == 'oldrange':
                lines += old[i:item[2]]
            else:
                raise SystemExit(f'{law["key"]} {key}: bad item {item}')
        if sub:
            return lines
        if re.search(r'\[\.\.\.\]|\(\.\.\.\)|…', ''.join(lines)):
            raise SystemExit(f'{law["key"]} {key}: an ellipsis left in the text')
        lines = [close_quote(l) if l.endswith(('”', '”.', '"')) else l for l in lines]
        if key in units and units[key]['lines'] == lines:
            continue
        lab = law.get('labels', {}).get(key)
        units[key] = {'label': lab or units.get(key, {}).get('label') or key,
                      'kind': units.get(key, {}).get('kind', 'art'), 'lines': lines}
        changed.append(key)
    return changed


def main(spec_path: str):
    spec = json.loads(Path(spec_path).read_text(encoding='utf-8'))
    nid = spec['nla_id']
    b = spec['base']
    units = nlaunits.units(nid, b['capture'], **spec.get('nla_args', {}))
    for k, v in spec.get('base_fix', {}).items():       # base units the parser cannot split (hand, listed in decisions)
        if k not in units:      # a provision the consolidation leaves out, added from its own law (listed in decisions)
            units[k] = {'label': spec.get('base_labels', {}).get(k, k), 'kind': spec.get('base_kinds', {}).get(k, 'provision'),
                        'lines': v}
        units[k]['lines'] = v
    bsrc = nlaunits.URL.format(id=nid, ts=b['capture'])
    versions = [{'from': b['date'], 'source_url': bsrc, 'sha256': hashlib.sha256(cached(bsrc).read_bytes()).hexdigest(),
                 'units': {k: as_unit(units[k]) for k in sorted(units)}, 'credits': {}, 'note': b['note']}]
    laws = {}
    results = {}
    cps = sorted(spec['checkpoints'], key=lambda c: c['date'])
    for law in sorted(spec['laws'], key=lambda l: (l['in_force'], l['key'])):
        for c in cps:
            if c['id'] not in results and c['date'] < law['in_force']:
                results[c['id']] = nladiff.diff(units, nlaunits.units(nid, c['capture'], **spec.get('nla_args', {})))
        if law.get('pending'):
            continue
        lp, lsha = law_paras(law)
        if os.environ.get('PARAS') == law['key']:
            for i, p in enumerate(lp):
                print(i, p[:160])
            return
        ch = apply_law(law, units, lp)
        if not ch:
            raise SystemExit(f'{law["key"]}: no change')
        v = {'from': law['in_force'], 'source_url': law['pdf'], 'sha256': lsha,
             'changes': {k: (as_unit(units[k]) if k in units else None) for k in sorted(ch)},
             'credits': {k: [law['key']] for k in sorted(ch)},
             'note': f'Wording of {law["label"]} from its El Peruano text ({law["pdf"]}).'}
        if versions[-1]['from'] == law['in_force']:
            v['same_day'] = True
        versions.append(v)
        laws[law['key']] = {k: law.get(k) for k in ('label', 'title', 'kind', 'enacted', 'published')} | \
            {'url': law['pdf'], 'temporary_until': None, 'restores': None, 'note': None}
        print(law['key'], law['in_force'], 'changed', ch)
    for c in cps:
        if c['id'] not in results:
            results[c['id']] = nladiff.diff(units, nlaunits.units(nid, c['capture'], **spec.get('nla_args', {})))
    name = spec['title_short']
    decisions = list(spec['decisions'])
    for law in sorted(spec['laws'], key=lambda l: l['in_force']):
        if law.get('pending'):
            decisions.append(f'{name}: {law["label"]} is not applied: {law["pending"]}')
        if law.get('vigencia'):
            decisions.append(f'{name}: {law["label"]} is in force on {law["in_force"]}: {law["vigencia"]}')
        if law.get('hand'):
            decisions.append(f'{name}: {law["label"]}: {law["hand"]}')
    bad = 0
    for c in cps:
        r = results[c['id']]
        ex = spec.get('explained', {}).get(c['id'], {})
        open_ = [x for x in r if x[0] not in ex]
        print('checkpoint %s (%s): %d differences, %d unexplained' % (c['id'], c['date'], len(r), len(open_)))
        for x in (open_ if not os.environ.get('DIFF') else r):
            print('   ', x[0], x[1], x[2][:300])
        bad += bool(open_)
        decisions.append(
            f'{name} checkpoint {c["id"]}: every provision rebuilt here equals Editora Perú\'s Normas Legales Actualizadas of '
            f'{c["date"]} (Internet Archive capture {c["capture"]}) word for word.' if not r else
            f'{name} checkpoint {c["id"]}: compared word for word, provision by provision, with Editora Perú\'s Normas '
            f'Legales Actualizadas of {c["date"]} (capture {c["capture"]}): {len(r)} differences, each explained here.')
        for k, kind, d in r:
            decisions.append(f'{name} checkpoint {c["id"]}, {k}: {ex.get(k, "UNEXPLAINED")}')
    pub = spec.get('publisher')
    act = {'slug': spec['slug'], 'short': spec['short'], 'title': spec['title'], 'url': spec['url'],
           'first_law': None, 'earlier_laws': spec.get('earlier_laws', []), 'versions': versions}
    if pub:
        act['publisher'] = pub
    for k, l in spec.get('extra_laws', {}).items():
        laws[k] = l
    part = {'laws': {k: laws[k] for k in sorted(laws)}, 'acts': [act], 'sources': spec['sources'],
            'decisions': decisions, 'ai_use': spec['ai_use']}
    if os.environ.get('DRY'):
        print('dry run:', len(versions), 'versions')
        return
    if bad:
        raise SystemExit('unexplained checkpoint differences: part not written')
    out = ROOT / 'corpus.d' / spec['part']
    tmp = out.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(part, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, out)
    print('wrote', out, len(versions), 'versions', len(laws), 'laws')


if __name__ == '__main__':
    main(sys.argv[1])
