# Chess Coach

Local-first chess analysis tool: PGN games in, Stockfish and optional Maia 2 context locally, Markdown/JSON/annotated PGN out.

Chess Coach now has three local interfaces:

- CLI: still supported for technical users and scripting.
- Local web GUI: a FastAPI server bound to `127.0.0.1` by default, serving a plain browser UI for Windows-native users without WSL assumptions.
- Electron desktop GUI: preserved as the existing desktop prototype/wrapper candidate.

There is still no hosted service, no analytics, and no data sent to Sangeev. Lichess requests go only to https://lichess.org when you explicitly ask for them. The new web GUI is local-only by default; it is not a hosted dashboard and there is still no dashboard service here.

## Current state

This public repository includes:

- Local CLI analysis pipeline.
- Local annotated PGN export.
- Explicit token-gated Lichess Study helpers.
- Local web GUI under `apps/web/static/` served by `python -m chess_coach web`.
- Local Electron desktop GUI under `apps/desktop/`.
- Shared local config file: `.env.stockfish`.

The local web GUI and desktop GUI both avoid automatic Study upload in the main workflow. The safe path is still: import public games, analyse locally, export annotated PGN, then review the PGN before importing it into Lichess yourself. Automatic Study upload is planned later, but not in this local-only slice.

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

## Local web GUI

The local web GUI is the preferred non-terminal path for Windows-native users in this slice.

What it does:

- serves a plain browser UI from a loopback-only FastAPI server by default
- reads and writes `.env.stockfish`
- shows inline config validation
- tests Stockfish and Maia readiness
- tests Lichess username/token access
- imports public Lichess games by username
- runs local analysis
- exports annotated PGN
- creates a local diagnostic bundle

What it deliberately does not do yet:

- any hosted backend
- any telemetry
- automatic Lichess Study creation/import as part of the main web workflow
- final Windows one-click packaging/installer

Run it locally:

```bash
python3 -m chess_coach web --host 127.0.0.1 --port 8765 --open
```

Alternative wrapper:

```bash
python3 scripts/run_web_gui.py
```

Open http://127.0.0.1:8765/ in a browser if you do not pass `--open`.

Local web privacy boundary:

- Binds to `127.0.0.1` by default
- Refuses non-loopback hosts unless `--allow-lan` is passed explicitly
- Your Lichess token is only sent to lichess.org
- Generated reports and PGNs stay on this machine
- Review the PGN before importing it into Lichess

Windows notes:

- No WSL is required for the intended user path
- Install Stockfish on Windows, then paste the full `stockfish.exe` path into the UI
- A packaged one-click `.exe` is still a future step after this dev-mode web GUI slice

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
