import sys, re; sys.path.insert(0,'more2')
import nlaunits, nladiff
kw = dict(start_marker='TEXTO ÚNICO ORDENADO DE LA LEY Nº 27806, LEY DE TRANSPARENCIA Y ACCESO A LA INFORMACIÓN PÚBLICA', end_marker=r'^REGLAMENTO DE LA LEY DE TRANSPARENCIA', sumillas=True, bold_breaks=True,
          notes=r'\s*\((?:Texto|Art[íi]culo|Numeral|Literal|P[áa]rrafo|Inciso)\s+(?:según|incorporad[oa]|modificad[oa]|derogad[oa]|sustituid[oa]|agregad[oa])[^()]*\)\.?', drop=r'^\(\*+\)\s')
a = nlaunits.units(20, '20240817', **kw)
b = nlaunits.units(20, '20260812', **kw)
for k, u in a.items():
    for l in u['lines']:
        if re.search(r'\((Texto|Art[íi]culo) ', l): print('LEAK', k, l[:200])
print(len(a), len(b))
for x in nladiff.diff(a, b): print(x)
if len(sys.argv) > 1:
    for k in sys.argv[1:]:
        print(k, a.get(k, {}).get('lines')); print(k, b.get(k, {}).get('lines'))
