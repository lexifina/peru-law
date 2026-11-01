"""Ops a checked DS listing saw without a card (recomputed from cached listing pages; fetches only what is uncached).
    python -X utf8 more9/missops.py FROM TO "DECRETO SUPREMO" """
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'more8'))
sys.argv = [sys.argv[0]] + sys.argv[1:]
sys.path.insert(0, str(ROOT / 'more2'))
import listing
fi, ff, tipo = sys.argv[1:4]
for pub in ('NL', 'EX'):
    cards, miss = listing.rng(fi, ff, tipo, pub)
    print(pub, len(cards), ' '.join(sorted(set(miss))), flush=True)
