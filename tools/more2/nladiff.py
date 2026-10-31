"""Word-level differences between two unit sets (NLA captures or a corpus state).
    python -X utf8 more2/nladiff.py ID TS1 TS2"""
import sys, re, difflib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import nlaunits

def words(lines):
    t = ' '.join(lines)
    t = t.replace('º', '°').replace('\xad', '').replace('“', '"').replace('”', '"')
    return re.findall(r'\w+(?:[-.]\w+)*', t.lower())

def diff(a, b):
    out = []
    for k in sorted(set(a) | set(b)):
        if k not in a: out.append((k, 'only-second', ' '.join(b[k]['lines'])[:200])); continue
        if k not in b: out.append((k, 'only-first', ' '.join(a[k]['lines'])[:200])); continue
        wa, wb = words(a[k]['lines']), words(b[k]['lines'])
        if wa != wb:
            sm = difflib.SequenceMatcher(None, wa, wb, autojunk=False)
            ds = ['%s[%s|%s]' % (op[0], ' '.join(wa[i1:i2][:12]), ' '.join(wb[j1:j2][:12])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal']
            out.append((k, 'words', '; '.join(ds)[:400]))
    return out

if __name__ == '__main__':
    a = nlaunits.units(sys.argv[1], sys.argv[2]); b = nlaunits.units(sys.argv[1], sys.argv[3])
    for x in diff(a, b): print(*x)
