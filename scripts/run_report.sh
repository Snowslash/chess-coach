#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${CHESS_COACH_VENV:-$HOME/.venvs/chess-coach}"

cd "$PROJECT_DIR"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  cat >&2 <<EOF
Chess Coach runtime venv not found: $VENV_DIR

Run one-time setup first:
  bash scripts/setup_wsl.sh

Then run this script again. This run script deliberately does not install dependencies.
EOF
  exit 2
fi

if [ -f ".env.stockfish" ]; then
  # shellcheck disable=SC1091
  source ".env.stockfish"
fi

PGN_PATH="${1:-${CHESS_COACH_PGN:-input/sample_games.pgn}}"
OUT_PATH="${2:-${CHESS_COACH_OUT:-reports/latest.md}}"
PLAYER="${3:-${CHESS_COACH_PLAYER:-}}"

if [ "${MAIA2_ENABLED:-false}" = "true" ] && [ ! -f "maia2_models/${MAIA2_GAME_TYPE:-rapid}_model.pt" ]; then
  cat >&2 <<EOF
Maia 2 is enabled but the expected local model file is missing:
  maia2_models/${MAIA2_GAME_TYPE:-rapid}_model.pt

Keep model files local and out of git. Re-run the one-time Maia/model setup before requesting Maia reports.
EOF
  exit 3
fi

ANALYSE_ARGS=("$VENV_DIR/bin/python" -m chess_coach analyse --pgn "$PGN_PATH" --out "$OUT_PATH")
if [ -n "$PLAYER" ]; then
  ANALYSE_ARGS+=(--player "$PLAYER")
fi
"${ANALYSE_ARGS[@]}"

JSON_PATH="${OUT_PATH%.*}.json"
"$VENV_DIR/bin/python" - "$OUT_PATH" "$JSON_PATH" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

markdown_path = Path(sys.argv[1])
json_path = Path(sys.argv[2])
if not json_path.exists():
    print(f"Chess Coach summary unavailable: JSON not found at {json_path}")
    raise SystemExit(0)

bundle = json.loads(json_path.read_text(encoding="utf-8"))
games = bundle.get("games", [])
patterns = bundle.get("patterns", {})
metadata = bundle.get("metadata", {})
print("Chess Coach summary")
print(f"- Markdown: {markdown_path}")
print(f"- JSON: {json_path}")
print(f"- Games: {len(games)}")
print(f"- Critical moments: {patterns.get('critical_moments', 0)}")
print(f"- Engine(s): {', '.join(sorted({g.get('analysis_engine', 'unknown') for g in games})) or 'unknown'}")
print(f"- stockfish_available: {all(g.get('stockfish_available') for g in games) if games else False}")
print(f"- maia2_enabled: {metadata.get('maia2_enabled', False)}")
print(f"- maia2_available: {metadata.get('maia2_available', False)}")
print(f"- maia2_reason: {metadata.get('maia2_reason', 'unknown')}")
priorities = patterns.get("training_priorities") or []
if priorities:
    print(f"- Top priority: {priorities[0]}")
PY
