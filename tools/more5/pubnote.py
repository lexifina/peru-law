"""Append the closing-quote REVISED note to the PUBLISH files of the parts it changed (idempotent)."""
from pathlib import Path

D = Path(__file__).resolve().parent.parent / 'corpus.d'
CH = {'61-lope': 'dc-05', '65-lpag': 'art-007, art-229, dcf-01', '73-relaciones-colectivas': 'art-007',
      '83-pesca': 'art-090', '86-codigo-procesal-civil': 'art-202', '87-poder-judicial': 'art-227'}
TAG = 'REVISED 2026-11-01 (inner closing quote)'
for part, keys in CH.items():
    p = D / (part + '.PUBLISH')
    s = p.read_text(encoding='utf-8').rstrip('\n')
    if TAG in s:
        continue
    s += (f' {TAG}: nla_args.balanced on; a paragraph ending in a quotation it opens itself (e.g. Diario Oficial “El '
          f'Peruano”.) now keeps its closing quotation mark and full stop, which changes only {keys} in the first version '
          f'(and the versions that carry it); each restored line equals the end of its paragraph in the Editora Perú '
          f'file; before/after diff of every corpus.d part shows nothing else (more5/baldiff.txt); checkpoints unchanged, '
          f'0 unexplained; merged scratch build 47 acts / 346 versions / 343 commits / 613 tags, check 0 mismatches / 0 '
          f'trailer errors, --compare identical, audit_push clean on main and futuro.')
    p.write_text(s + '\n', encoding='utf-8', newline='\n')
    print('noted', part)
