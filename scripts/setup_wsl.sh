#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${CHESS_COACH_VENV:-$HOME/.venvs/chess-coach}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_DIR"

if [ -d ".venv" ] || [ -L ".venv" ]; then
  echo "Removing project-local .venv from Windows-mounted folder: $PROJECT_DIR/.venv"
  rm -rf .venv
fi

echo "Creating WSL-native venv: $VENV_DIR"
mkdir -p "$(dirname "$VENV_DIR")"
"$PYTHON_BIN" -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip
python -m pip install -e '.[dev,maia2]'

python -m pytest -q

cat <<EOF

Setup complete.

Use this venv with:
  source "$VENV_DIR/bin/activate"
  cd "$PROJECT_DIR"

Configure local runtime:
  cp .env.example .env.stockfish
  # edit STOCKFISH_PATH and optional Maia/default player settings

Import public Lichess games:
  python -m chess_coach import-lichess --user your_lichess_username --max 20 --out input/lichess_recent_your_lichess_username.pgn

Run a report:
  bash scripts/run_report.sh input/lichess_recent_your_lichess_username.pgn reports/lichess_recent_maia2.md your_lichess_username
EOF
