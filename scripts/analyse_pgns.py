#!/usr/bin/env python3
from __future__ import annotations
import subprocess, sys
from pathlib import Path
def main(argv):
    if len(argv) not in (2,3): print("Usage: python scripts/analyse_pgns.py <input.pgn> [reports/latest.md]", file=sys.stderr); return 2
    pgn=Path(argv[1]); out=Path(argv[2]) if len(argv)==3 else Path("reports/latest.md"); cmd=[sys.executable,"-m","chess_coach","analyse","--pgn",str(pgn),"--out",str(out)]
    c=subprocess.run(cmd,check=False,text=True,capture_output=True); print(c.stdout.rstrip() if c.stdout else ""); print(c.stderr.rstrip() if c.stderr else "", file=sys.stderr)
    if c.returncode==0: print(f"Hermes wrapper result: Markdown report at {out}; JSON at {out.with_suffix('.json')}")
    return c.returncode
if __name__=="__main__": raise SystemExit(main(sys.argv))
