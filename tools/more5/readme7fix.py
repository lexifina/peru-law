"""Move the round's README bullets right after the Ley del Procedimiento Administrativo General bullet of each section."""
from pathlib import Path

P = Path(__file__).resolve().parent.parent / 'repo' / 'README.md'
lines = P.read_text(encoding='utf-8').split('\n')
NEW = ('- **Decretos Legislativos 713', '- **Ley sobre Modalidades Formativas', '- **Leyes 28518 and 26644',
       '- **Leyes 27908', '- **Leyes 29245')
moved = [l for l in lines if l.startswith(NEW)]
lines = [l for l in lines if not l.startswith(NEW)]
check = [l for l in moved if 'Each' in l]
limit = [l for l in moved if 'Each' not in l]
for group, head in ((check, '- **Ley del Procedimiento Administrativo General (Texto'),
                    (limit, '- **Ley del Procedimiento Administrativo General:')):
    i = [n for n, l in enumerate(lines) if l.startswith(head)][0]
    lines[i + 1:i + 1] = group
P.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
print(len(check), len(limit))
