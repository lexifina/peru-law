"""Run a command at BelowNormal priority, record its PID, wait, and pass its exit code on.
    python more3/run.py LOGFILE CMD ARGS..."""
import subprocess, sys, time
from pathlib import Path
log = Path(sys.argv[1])
with log.open('a', encoding='utf-8') as fh:
    p = subprocess.Popen(sys.argv[2:], stdout=fh, stderr=subprocess.STDOUT, creationflags=0x00004000)
    with (Path(__file__).resolve().parent / "pids.txt").open('a') as pf:
        pf.write(f'{time.strftime("%Y-%m-%dT%H:%M:%S")} {p.pid} {" ".join(sys.argv[2:])[:200]}\n')
    sys.exit(p.wait())
