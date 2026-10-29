"""Discovery helper: print the document PDF links of a gob.pe page (fetched through cfetch)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cfetch  # noqa: E402

for u in sys.argv[1:]:
    p = cfetch.get(u)
    t = p.read_text("utf8", "replace") if p else ""
    links = sorted(set(re.findall(r'https://cdn\.www\.gob\.pe/uploads/document/file/[^"\s<>]+', t)))
    for x in links:
        if "preview" not in x and "thumb" not in x:
            print(x)
