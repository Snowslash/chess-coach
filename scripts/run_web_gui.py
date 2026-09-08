"""Browser-first source/PyInstaller launcher; working data stays in the launch folder."""
import sys
from pathlib import Path

from chess_coach.cli import main


if __name__ == "__main__":
    options = sys.argv[1:] or ["--open"]
    raise SystemExit(main(["web", "--project-root", str(Path.cwd()), *options]))
