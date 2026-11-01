"""Suspicious mid-line items/numbers in a lawact DRY FULL dump (stdin)."""
import re, sys
cur = None
for l in sys.stdin.read().splitlines():
    if l.startswith('== '):
        cur = l; continue
    for m in re.finditer(r'(?<=[.:;])\s+(?:[a-zñ]\)|[a-z]\.|\d{1,2}\.\d{1,2}\.?|\d{1,2}\.-|[ivx]+\))\s+[A-ZÁÉÍÓÚa-z]', l):
        print(cur[:30], '|', l[max(0, m.start() - 60):m.end() + 40])
    if len(l) > 1 and l[0].islower():
        print(cur[:30], '| LOWER START |', l[:80])
