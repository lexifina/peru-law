"""List cached cards whose sumilla looks like a new framework law (cache only)."""
import json, glob, re
seen=set()
rx=re.compile(r'^(Ley (General|Org[áa]nica|Marco|del|de la|de los|de las|de)\b|C[óo]digo|Nueva Ley|Decreto Legislativo (del|de la|de) )', re.I)
bad=re.compile(r'modific|declara|crea la Universidad|crea el distrito|incorpora|precisa|prorroga|amplía|autoriza|deroga|exonera|interés nacional|Presupuesto|Endeudamiento|Equilibrio', re.I)
for f in sorted(glob.glob('.tmp/cards_*.jsonl')):
    for l in open(f,encoding='utf-8'):
        c=json.loads(l)
        if c['op'] in seen: continue
        seen.add(c['op'])
        s=c.get('sumilla','')
        if rx.search(s) and not bad.search(s):
            print(c['op'],c['tipo'][:6],c['numero'],'|',s[:120])
