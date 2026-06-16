# Chess Coach

Small local chess-coaching CLI: **PGN games in → Stockfish/mock analysis JSON out → Markdown coaching report out**.

The scope is deliberately boring: no dashboard, no web app and no hosted service. It runs locally, writes local reports and keeps licensed runtime artifacts out of git.

## Current state

This public repository is a clean single-commit release of the local Chess Coach project. It includes:

- v1 local longitudinal coaching workflow: import games, analyse, update local coach state, generate cards, training plans and weekly reviews.
- v2 first slice: local annotated PGN export for reviewing Chess Coach comments on a board, for example by manually importing the PGN into a private/unlisted Lichess Study.
- No Lichess token handling, no Lichess Study API integration and no hosted service yet.

## What it does

- Parses PGN files.
- Identifies the colour played by the target player.
- Analyses only that player's moves when the player is known.
- Uses Stockfish for tactical/evaluation signals when configured.
- Falls back to mock analysis for pipeline tests if Stockfish is unavailable.
- Optionally adds Maia 2 human-likeness context when Maia is installed and enabled.
- Exports annotated PGN comments from existing analysis JSON for board-based review.
- Writes:
  - Markdown report: human-readable coaching notes.
  - JSON report: structured per-game/per-move data.
  - Annotated PGN: optional local review export.

## Requirements

- Python 3.11+
- `python-chess` via this package's Python dependency list — this is the Python library, **not the PyChess GUI**.
- `pydantic` via this package's Python dependency list.
- Optional: Stockfish local binary for real engine analysis.
- Optional: Maia 2 Python package/runtime for human-likeness move probabilities.

## Quick start

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,maia2]'
python -m pytest -q
```

On WSL with a Windows-mounted project folder, prefer the helper below instead of creating `.venv` inside the project. Windows-mounted virtualenvs can produce `Permission denied` or externally-managed-environment weirdness.

```bash
bash scripts/setup_wsl.sh
```

That creates/reuses a WSL-native venv at:

```text
$HOME/.venvs/chess-coach
```

## Install Stockfish

Stockfish is the tactical evaluator. It is GPL-3.0 and is **not vendored** in this repository.

Linux/WSL:

```bash
sudo apt update
sudo apt install stockfish
which stockfish || test -x /usr/games/stockfish
```

macOS:

```bash
brew install stockfish
which stockfish
```

Windows:

- Install Stockfish from https://stockfishchess.org/download/
- Note the full path to `stockfish.exe`.
- If running through WSL, either install Stockfish inside WSL or use a WSL-visible path to the Windows binary.

## Configure local runtime

Copy the example env file and edit it for your machine:

```bash
cp .env.example .env.stockfish
```

Example values:

```bash
export STOCKFISH_PATH=/usr/games/stockfish
export STOCKFISH_DEPTH=12
export STOCKFISH_TIME_LIMIT=0.1
export MAIA2_ENABLED=true
export MAIA2_GAME_TYPE=rapid
export MAIA2_DEVICE=cpu
export MAIA2_TARGET_ELO=1500
export CHESS_COACH_PLAYER=your_lichess_username
```

`.env.stockfish` is intentionally ignored by git. Do not commit machine-specific paths, usernames if you prefer not to publish them, Stockfish binaries, Maia model weights or generated reports.

## Install / enable Maia 2

Maia 2 is optional. It does not replace Stockfish.

- Stockfish = tactical truth: eval changes, blunders, missed wins, best moves.
- Maia 2 = human-likeness context: how likely a move is for players around a target Elo.

Install the optional dependency group:

```bash
python -m pip install -e '.[maia2]'
```

Enable it in `.env.stockfish`:

```bash
export MAIA2_ENABLED=true
export MAIA2_GAME_TYPE=rapid
export MAIA2_DEVICE=cpu
export MAIA2_TARGET_ELO=1500
```

The code uses the Maia 2 Python package runtime. The runtime may download/use model weights. Keep any Maia model weights/assets local and out of git. If Maia is enabled but unavailable, the report remains a valid Stockfish report and includes `maia2_reason` in the JSON/summary explaining what is missing.

## Import games from Lichess

For public Lichess games:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --out input/lichess_recent_your_lichess_username.pgn
```

For a narrower recent-game pull:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --perf rapid --rated-only --since-days 14 --out input/lichess_recent_your_lichess_username.pgn
```

Then analyse them:

```bash
python -m chess_coach analyse \
  --pgn input/lichess_recent_your_lichess_username.pgn \
  --out reports/lichess_recent.md \
  --player your_lichess_username
```

Imported personal PGN dumps under `input/lichess_recent*.pgn` and `input/lichess_pgn_*.pgn` are ignored by git. Commit only deliberate sample fixtures.

## v1 longitudinal workflow

This v1 flow stays local-only and CLI-first: no dashboard, no web app, and no hosted service.

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

Privacy/runtime boundary:

- `.coach/` and `.coach/state.json` are ignored local coaching state.
- Generated reports, review cards, training plans and imported personal PGNs are ignored by git.
- Stockfish remains the tactical truth layer.
- Maia 2 remains optional human-likeness annotation.
- If Maia 2 is unavailable, the Stockfish/mock workflow should still be understandable.

## Normal repeated use

After setup, use the stable wrapper:

```bash
bash scripts/run_report.sh
```

Defaults can be supplied through `.env.stockfish`:

```bash
export CHESS_COACH_PGN=input/lichess_recent_your_lichess_username.pgn
export CHESS_COACH_OUT=reports/lichess_recent_maia2.md
export CHESS_COACH_PLAYER=your_lichess_username
```

Or pass them directly:

```bash
bash scripts/run_report.sh input/my_games.pgn reports/my_report.md your_lichess_username
```

The wrapper prints a post-run summary including engine, `stockfish_available`, `maia2_enabled`, `maia2_available`, `maia2_reason` and top priority.

## Mock/smoke run

If you only want to verify the pipeline without Stockfish:

```bash
python -m chess_coach analyse --pgn input/sample_games.pgn --out reports/latest.md --mock
```

Do not draw chess conclusions from mock-only output.

## Outputs

Typical outputs:

```text
reports/latest.md
reports/latest.json
reports/lichess_recent.md
reports/lichess_recent.json
```

Reports include:

- executive diagnosis;
- recurring weaknesses;
- important mistakes;
- opening/middlegame/endgame notes;
- 7-day plan adapted from the report's dominant phase, colour and error class;
- critical positions with FENs and Lichess analysis URLs;
- uncertainty notes;
- raw file pointers.

Generated reports are ignored by default.

Longitudinal coach state also stays local-only under `.coach/`. Treat `.coach/` as ignored local coaching state: it is for personal history and derived memory, not for git.

## v2 local annotated PGN export

The first v2 slice stays local-only and privacy-preserving.

```bash
python -m chess_coach export-annotated-pgn \
  --from reports/latest.json \
  --out reports/annotated/latest.pgn \
  --max-games 10 \
  --critical-only
```

What this slice does:

- Reads existing Chess Coach analysis JSON.
- Reconstructs legal move order with `python-chess`.
- Writes a parseable annotated PGN with concise `Chess Coach:` comments on critical moments.
- Keeps generated annotated PGNs local and ignored by git under `reports/annotated/*.pgn`.

What this slice does not do:

- no token required.
- no network required.
- No Lichess API calls.
- No Lichess Study creation/import yet.

The Lichess Study API layer is planned later, after the local annotated PGN flow is proven useful.

## Tests

```bash
python -m pytest -q
```

## GitHub / release hygiene

Before publishing:

```bash
git status --ignored
git check-ignore -v .env.stockfish maia2_models/rapid_model.pt reports/lichess_recent_maia2.json input/lichess_recent_your_lichess_username.pgn
git add --dry-run .
python -m pytest -q
```

Expected: local env files, Stockfish binaries, Maia model weights/assets, generated reports, virtualenvs, egg-info, pycache and imported personal PGNs are not staged.

## Licence

This repository is licensed under **GPL-3.0-or-later**. See `LICENSE` and `docs/licensing.md`.

Why GPL: this project directly depends on `python-chess`, which is GPL-3.0-or-later. Stockfish is GPL-3.0 and is invoked only as a user-installed local UCI engine; it is not vendored here. Maia 2 is MIT-licensed, but Maia model weights/assets remain local runtime artifacts and are not committed.
