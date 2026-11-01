"""Base units of the TUO CEP (NLA 70006 capture 20250523) with the args under test: python -X utf8 more7/cepunits.py [KEY..]"""
import json, sys
sys.path.insert(0, 'more2'); sys.path.insert(0, 'more5')
import nlaunits
from specs import A
NOTES = (r"\s*\((?:Texto|Art[íi]culo|Numeral|Literal|P[áa]rrafo|Inciso|Cap[íi]tulo|Denominaci[óo]n)\s+(?:modificad[oa]\s+)?"
         r"(?:según|incorporad[oa]|modificad[oa]|derogad[oa]|sustituid[oa]|agregad[oa]|rectificad[oa])[^()]*\)\.?")
ARGS = A | {"end_marker": "^REGLAMENTO DEL CÓDIGO DE EJECUCIÓN PENAL$", "notes": NOTES, "drop": "^\(\*+\)\s"}
if __name__ == '__main__':
    u = nlaunits.units(70006, '20250523', **ARGS)
    keys = sys.argv[1:]
    for k, v in u.items():
        if keys and k not in keys:
            continue
        if keys:
            print('==', k, v['label']); print('\n'.join(v['lines']))
        else:
            print(k, '|', v['lines'][0][:90], '| n', len(v['lines']))
