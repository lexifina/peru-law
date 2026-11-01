"""Append the full-stop REVISED note to the PUBLISH files of the parts the fix changed (idempotent)."""
from pathlib import Path

D = Path(__file__).resolve().parent.parent / 'corpus.d'
CH = {'62-control': (1, 'art-022'), '63-hostigamiento': (1, 'dcf-03'),
      '71-sociedades': (6, 'art-009, art-010, art-023, art-188 (2), df-09'), '76-carrera-administrativa': (1, 'art-054'),
      '81-seguridad-salud-trabajo': (3, 'art-013, art-026, art-060'), '84-bienestar-animal': (2, 'dcm-01, dcm-02'),
      '88-codigo-tributario': (1, 'art-034'), '90-cna': (3, 'art-003-a, art-092, art-112-a'), '94-transporte': (1, 'art-029'),
      '95-universitaria': (2, 'art-005, art-010'), '9f-tributacion-municipal': (7, 'art-006 (2), art-008, art-009, art-018, art-019 (2)')}
TAG = 'REVISED 2026-11-01 (full stop after Editora\'s closing mark)'
for part, (n, keys) in CH.items():
    p = D / (part + '.PUBLISH')
    s = p.read_text(encoding='utf-8').rstrip('\n')
    if TAG in s:
        continue
    s += (f' {TAG}: a base-text line ending in Editora Perú\'s closing quotation mark and a full stop now keeps the full '
          f'stop (the mark is still dropped; same rule as replayed wording, not when the wording already ends in '
          f'punctuation): {n} line(s) restored ({keys}) in the first version and the versions that carry them; each '
          f'restored line ends that way in the Editora Perú file (more7/fsverify.py); before/after diff of every corpus.d '
          f'part shows nothing else (more7/fullstop9.txt), 31 other parts byte-identical; checkpoints unchanged, 0 '
          f'unexplained; two parses identical; merged scratch build 52 acts / 352 commits / 627 tags, check 0 mismatches '
          f'/ 0 trailer errors, --compare identical, audit_push clean on main and futuro.')
    p.write_text(s + '\n', encoding='utf-8', newline='\n')
    print('noted', part)
