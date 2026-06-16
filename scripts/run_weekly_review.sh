#!/usr/bin/env bash
set -euo pipefail

if [ -f .env.stockfish ]; then
  # shellcheck disable=SC1091
  source .env.stockfish
fi

VENV="${CHESS_COACH_VENV:-$HOME/.venvs/chess-coach}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Chess Coach runtime venv not found: $VENV" >&2
  echo "Run one-time setup first: bash scripts/setup_wsl.sh" >&2
  exit 2
fi

USER_NAME="${CHESS_COACH_PLAYER:?Set CHESS_COACH_PLAYER in .env.stockfish or environment}"
PGN="${CHESS_COACH_PGN:-input/lichess_recent_${USER_NAME}.pgn}"
REPORT="${CHESS_COACH_OUT:-reports/lichess_recent_maia2.md}"
CARDS="${CHESS_COACH_CARDS_OUT:-reports/cards/lichess_recent_cards.md}"
PLAN="${CHESS_COACH_TRAINING_OUT:-reports/training_plan.md}"
WEEKLY="${CHESS_COACH_WEEKLY_OUT:-reports/weekly_review.md}"

"$VENV/bin/python" -m chess_coach import-lichess --user "$USER_NAME" --max "${CHESS_COACH_MAX_GAMES:-20}" --out "$PGN"
"$VENV/bin/python" -m chess_coach analyse --pgn "$PGN" --out "$REPORT" --player "$USER_NAME" --update-state
"$VENV/bin/python" -m chess_coach cards --from "${REPORT%.md}.json" --out "$CARDS"
"$VENV/bin/python" -m chess_coach training-plan --from "${REPORT%.md}.json" --out "$PLAN"
"$VENV/bin/python" -m chess_coach weekly-review --out "$WEEKLY"
