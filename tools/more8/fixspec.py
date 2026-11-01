"""One-off: put the escapes back in more8/specs11.py lines 23-24 (a shell heredoc turned them into raw characters)."""
from pathlib import Path
p = Path(__file__).resolve().parent / 'specs11.py'
s = p.read_text(encoding='utf-8')
s = s.replace('\x08', '\\b').replace("SHY = ['­', '']", "SHY = ['\\u00ad', '']")
p.write_text(s, encoding='utf-8', newline='\n')
