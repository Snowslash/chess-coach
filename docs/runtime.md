# Chess Coach runtime

This project should be easy to run repeatedly without reinstalling Stockfish or Maia every time.

## One-time setup

Run this once from WSL for the persistent local runtime:

```bash
cd "/mnt/c/Users/<you>/Documents/Coding Projects/chess-coach"
bash scripts/setup_wsl.sh
```

That creates or refreshes a WSL-native virtual environment at:

```text
$HOME/.venvs/chess-coach
```

Keep the virtual environment out of the Windows-mounted project folder. This avoids Windows permission weirdness and means normal runs reuse the same Python environment.

## Dependencies

The Python dependency is `python-chess`, not the PyChess GUI application. The setup script installs the project with:

```bash
python -m pip install -e '.[dev,maia2]'
```

Install Stockfish locally through your host/system package manager and point `.env.stockfish` at that local binary. Keep `.env.stockfish` local; do not commit it.

Keep Maia runtime packages and model files local as well. `maia2_models/` is ignored by git and should stay that way.

## Local configuration

```bash
cp .env.example .env.stockfish
```

Then edit:

```bash
export STOCKFISH_PATH=/path/to/stockfish
export MAIA2_ENABLED=true
export CHESS_COACH_PGN=input/lichess_recent_your_lichess_username.pgn
export CHESS_COACH_OUT=reports/lichess_recent_maia2.md
export CHESS_COACH_PLAYER=your_lichess_username
```

## Import Lichess games

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --out input/lichess_recent_your_lichess_username.pgn
```

Or use the recent-game filters for a tighter local review window:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --perf rapid --rated-only --since-days 14 --out input/lichess_recent_your_lichess_username.pgn
```

Imported personal PGNs are ignored by git by default.

## v1 longitudinal workflow

This workflow remains local-only and CLI-first. No dashboard, no web app, and no hosted service are part of v1.

1. Import recent games.
2. Analyse and update local coach state.
3. Generate review cards.
4. Generate measurable training plan.
5. Generate weekly review.

Example commands:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --perf rapid --rated-only --since-days 14 --out input/lichess_recent_your_lichess_username.pgn
python -m chess_coach analyse --pgn input/lichess_recent_your_lichess_username.pgn --out reports/lichess_recent_maia2.md --player your_lichess_username --update-state
python -m chess_coach cards --from reports/lichess_recent_maia2.json --out reports/cards/lichess_recent_cards.md
python -m chess_coach training-plan --from reports/lichess_recent_maia2.json --out reports/training_plan.md
python -m chess_coach weekly-review --out reports/weekly_review.md
bash scripts/run_weekly_review.sh
```

Use `bash scripts/run_weekly_review.sh` when you want the boring default flow without typing each command.

## Normal run

After setup, run reports with:

```bash
bash scripts/run_report.sh
```

For the full longitudinal flow, use:

```bash
bash scripts/run_weekly_review.sh
```

The wrapper reads `.env.stockfish`, uses the persistent venv and prints a JSON-derived summary including `stockfish_available`, `maia2_enabled`, `maia2_available` and `maia2_reason`.

Override paths if needed:

```bash
bash scripts/run_report.sh input/my_games.pgn reports/my_report.md your_lichess_username
```

The run script deliberately does not reinstall dependencies. If the venv, Stockfish binary or Maia local model is missing, it fails with a setup message rather than silently doing a heavyweight reinstall.

## Local longitudinal state

When you want repeated coaching runs to accumulate history, keep that state under `.coach/`, typically `.coach/state.json`. This is ignored local coaching state: personal game history and derived coaching memory should stay out of git.

Generated reports, review cards, training plans and imported personal PGNs are also local ignored artifacts.

Generated annotated PGNs from `export-annotated-pgn` are local ignored artifacts too. Write them under `reports/annotated/latest.pgn` or another path under `reports/annotated/`.

## v2 local annotated PGN export

The first v2 slice is still local-only. It does not need a token, does not make network calls and does not talk to the Lichess Study API yet.

```bash
python -m chess_coach export-annotated-pgn \
  --from reports/latest.json \
  --out reports/annotated/latest.pgn \
  --max-games 10 \
  --critical-only
```

This reads an existing analysis JSON bundle, reconstructs the moves with `python-chess`, and writes a parseable annotated PGN with concise `Chess Coach:` comments on critical moments.

The Lichess Study API layer is planned later. It is not part of this slice.

## Runtime boundary

- Stockfish remains the tactical truth layer.
- Maia 2 remains optional human-likeness annotation.
- If Maia 2 is unavailable, the Stockfish/mock workflow should remain understandable.

## Git/licence hygiene

Do not commit:

```text
.env.stockfish
.env.* except .env.example/.env.sample
maia2_models/
*.pt
*.pth
*.onnx
*.bin
stockfish/
engines/
models/
reports/*.json
reports/**/*.json
reports/*.md
reports/**/*.md
reports/annotated/*.pgn
.coach/
*.coach.json
dist/
build/
input/lichess_recent*.pgn
input/lichess_pgn_*.pgn
```

The repository should contain integration code, tests and placeholder configuration only. Third-party engines/model weights are local runtime dependencies with their own licences.

For the full publishing/licence rationale, see `docs/licensing.md`. The short version: publish Chess Coach as GPL-3.0-or-later because it directly depends on GPL-3.0-or-later `python-chess`; do not vendor Stockfish binaries, Maia model weights/assets, local env files or generated analysis artifacts.
