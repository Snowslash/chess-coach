# Chess Coach

Local-first chess analysis tool: PGN games in, Stockfish and optional Maia 2 context locally, Markdown/JSON/annotated PGN out.

Chess Coach now has two local interfaces:

- CLI: still supported for technical users and scripting.
- Electron desktop GUI: for non-technical users who should not need the terminal or direct config-file editing.

There is still no hosted service, no analytics, and no data sent to Sangeev. Lichess requests go only to https://lichess.org when you explicitly ask for them. There is no dashboard or hosted web surface here; the GUI is a local desktop shell.

## Current state

This public repository includes:

- Local CLI analysis pipeline.
- Local annotated PGN export.
- Explicit token-gated Lichess Study helpers.
- Local Electron desktop GUI under `apps/desktop/`.
- Shared local config file: `.env.stockfish`.

The desktop GUI does not upload a Study automatically in this slice. The safe path is still: import public games, analyse locally, export annotated PGN, then review the PGN before importing it into Lichess yourself. Automatic Study upload is planned later, but not in this local-only desktop slice.

## What it does

- Parses PGN files.
- Identifies the colour played by the target player.
- Analyses that player’s moves when the player is known.
- Uses Stockfish for tactical/evaluation signals when configured.
- Falls back to mock analysis for pipeline smoke tests if Stockfish is unavailable.
- Optionally adds Maia 2 human-likeness context when Maia is installed and enabled.
- Imports public Lichess games by username.
- Exports annotated PGN comments from existing analysis JSON for board-based review.
- Writes local Markdown reports, local JSON bundles, and local annotated PGNs.

## Requirements

- Python 3.11+
- `python-chess` from this package’s dependencies — this is the Python library, not the PyChess GUI.
- `pydantic`
- Optional: local Stockfish binary
- Optional: local Maia 2 runtime
- Optional for the desktop GUI: Node.js 20+ and npm

## Shared configuration

Both CLI and desktop GUI read and write the same local file:

```text
.env.stockfish
```

That file is ignored by git. Environment variables still override file values in Python exactly as before.

Key values exposed in the GUI:

- `CHESS_COACH_PLAYER`
- `LICHESS_TOKEN`
- `CHESS_COACH_PGN`
- `CHESS_COACH_OUT`
- `STOCKFISH_PATH`
- `STOCKFISH_DEPTH`
- `STOCKFISH_TIME_LIMIT`
- `MAIA2_ENABLED`
- `MAIA2_GAME_TYPE`
- `MAIA2_DEVICE`
- `MAIA2_TARGET_ELO`

## Quick start: Python runtime

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev,maia2]'
python -m pytest -q
```

On WSL with a Windows-mounted project folder, prefer:

```bash
bash scripts/setup_wsl.sh
```

That creates or reuses a WSL-native venv at:

```text
$HOME/.venvs/chess-coach
```

## Install Stockfish

Stockfish is the tactical evaluator. It is GPL-3.0 and is not vendored in this repository.

Linux / WSL:

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

- Download from https://stockfishchess.org/download/
- Note the full path to `stockfish.exe`
- If you run the CLI through WSL, either install Stockfish inside WSL or use a WSL-visible path to the Windows binary

## Configure local runtime

Copy the example config file:

```bash
cp .env.example .env.stockfish
```

Typical values:

```bash
export STOCKFISH_PATH=/usr/games/stockfish
export STOCKFISH_DEPTH=12
export STOCKFISH_TIME_LIMIT=0.1
export CHESS_COACH_PLAYER=your_lichess_username
export CHESS_COACH_PGN=input/lichess_recent_your_lichess_username.pgn
export CHESS_COACH_OUT=reports/lichess_recent.md
export MAIA2_ENABLED=true
export MAIA2_GAME_TYPE=rapid
export MAIA2_DEVICE=cpu
export MAIA2_TARGET_ELO=1500
```

Optional token note:

- `LICHESS_TOKEN` is optional for public username imports.
- A token may help with rate limits or later private/token-gated Lichess actions.
- The desktop GUI only sends it to `lichess.org`.
- Keep it local and out of git.

## Desktop GUI

The desktop app is under `apps/desktop/` and uses Electron as a local shell around the existing Python engine.

What the GUI does in this slice:

- Read and write `.env.stockfish`
- Inline validation
- Test Stockfish and Maia readiness
- Test Lichess username/token access
- Import public Lichess games by username
- Run local analysis
- Export annotated PGN
- Export/import settings
- Create a local diagnostic bundle

What it deliberately does not do yet:

- automatic Study creation/import as part of the main GUI workflow
- any hosted backend
- any telemetry

Run it locally:

```bash
cd apps/desktop
npm install
npm run start
```

Desktop privacy boundary copy:

- Runs locally.
- Your Lichess token is only sent to lichess.org.
- Generated reports and PGNs stay on this machine.
- Review the PGN before importing it into Lichess.

## CLI workflow

### Import public Lichess games

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --out input/lichess_recent_your_lichess_username.pgn
```

With recent-game filters:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --perf rapid --rated-only --since-days 14 --out input/lichess_recent_your_lichess_username.pgn
```

### Analyse games

```bash
python -m chess_coach analyse --pgn input/lichess_recent_your_lichess_username.pgn --out reports/lichess_recent.md --player your_lichess_username --update-state
```

Equivalent wrapped form:

```bash
python -m chess_coach analyse \
  --pgn input/lichess_recent_your_lichess_username.pgn \
  --out reports/lichess_recent.md \
  --player your_lichess_username \
  --update-state
```

### Export annotated PGN

```bash
python -m chess_coach export-annotated-pgn \
  --from reports/lichess_recent.json \
  --out reports/annotated/lichess_recent.pgn \
  --max-games 10 \
  --critical-only
```

### Repeated local run

```bash
bash scripts/run_report.sh
```

The script prints a compact summary including `stockfish_available`, `maia2_enabled`, `maia2_available`, and `maia2_reason`.

## v1 longitudinal workflow

```bash
python -m chess_coach cards --from reports/lichess_recent.json --out reports/cards/lichess_recent_cards.md
python -m chess_coach training-plan --from reports/lichess_recent.json --out reports/training_plan.md
python -m chess_coach weekly-review --out reports/weekly_review.md
bash scripts/run_weekly_review.sh
```

## Lichess Study helpers

These remain explicit CLI actions, not part of the main GUI loop.

Create a dedicated OAuth token with only the `study:write` scope, keep it in `.env.stockfish`, and run the commands explicitly.

```bash
export LICHESS_TOKEN=replace_me_with_a_local_token
```

Create Study:

```bash
python -m chess_coach lichess-study-create \
  --name "Chess Coach Review 2026-06-18" \
  --visibility private \
  --token-env LICHESS_TOKEN
```

Import annotated PGN into that Study:

```bash
python -m chess_coach lichess-study-import \
  --study-id abc123 \
  --pgn reports/annotated/lichess_recent.pgn \
  --orientation white \
  --token-env LICHESS_TOKEN
```

Semantics:

- `private` and `unlisted` are supported
- public support intentionally absent
- import appends chapters
- it does not edit original Lichess games
- it does not auto-publish anything

## Privacy and local boundary

- No analytics
- No telemetry
- No hosted service
- No data sent to Sangeev
- Imported personal PGNs, generated reports, `.coach/state.json`, and other ignored local coaching state stay local ignored artifacts
- Stockfish binaries and Maia model weights remain local runtime dependencies and are not vendored here

## Outputs

Typical outputs:

```text
reports/latest.md
reports/latest.json
reports/annotated/latest.pgn
reports/cards/lichess_recent_cards.md
reports/training_plan.md
reports/weekly_review.md
```

Generated reports and PGNs are ignored by default.

## Tests

Python:

```bash
uv run --with pytest --with python-chess --with pydantic python -m pytest -q
```

Desktop app:

```bash
cd apps/desktop
npm install
npm test
npm run build
```

## GitHub / release hygiene

Before publishing:

```bash
git status --ignored
git check-ignore -v .env.stockfish maia2_models/rapid_model.pt reports/lichess_recent.json input/lichess_recent_your_lichess_username.pgn apps/desktop/node_modules
git add --dry-run .
uv run --with pytest --with python-chess --with pydantic python -m pytest -q
```

Expected: local env files, engine/model artifacts, imported PGNs, generated reports, local coaching state, and Electron dependencies are not staged.

## Licence

This repository is licensed under GPL-3.0-or-later. See `LICENSE` and `docs/licensing.md`.

Why GPL: this project directly depends on `python-chess`, which is GPL-3.0-or-later. Stockfish is GPL-3.0 and is invoked only as a user-installed local UCI engine; it is not vendored here. Maia 2 is MIT-licensed, but Maia model weights/assets remain local runtime artifacts and are not committed.
