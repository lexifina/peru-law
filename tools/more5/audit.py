"""private.audit_push on a scratch build: python -X utf8 more5/audit.py .tmp-<tag>-a"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'gitlaw_common'))
import private  # noqa: E402

r = Path(sys.argv[1])
for b in ['main', 'futuro']:
    f = private.audit_push(r, b)
    print('AUDIT', b, 'findings', len(f), f[:5])
