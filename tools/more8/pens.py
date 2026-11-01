"""nla_args under test for the pension acts (NLA 44 TUO SPP, NLA 45 D.Ley 19990)."""
import sys
sys.path.insert(0, 'more5')
from specs import A
NOTES = (r"\s*\(\*+\)\s*(?:Art[íi]culo|Numeral|Literal|P[áa]rrafo|Inciso|Cap[íi]tulo|T[íi]tulo|Disposici[óo]n|Ep[íi]grafe|Denominaci[óo]n|Texto)"
         r"[^()]*?(?:modificad|incorporad|derogad|sustituid|agregad|rectificad|precisad|adicionad)[\s\S]*$")
ARGS = {
    44: A | {"start_marker": "^TEXTO ÚNICO ORDENADO DE LA LEY DEL SISTEMA PRIVADO DE ADMINISTRACIÓN DE FONDOS DE PENSIONES$",
             "end_marker": "^(?:ANEXO 1|REGLAMENTO DEL TEXTO ÚNICO ORDENADO)"},
    45: A | {"end_marker": "^Dado en la Casa de Gobierno"},
}
