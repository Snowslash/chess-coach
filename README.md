# Chess Coach

Local-first chess analysis tool: PGN games in, Stockfish and optional Maia context locally, Markdown/JSON/annotated PGN out.

There is no hosted service, no analytics and no telemetry. Lichess requests go only to `lichess.org` when you explicitly import games or use Lichess actions. Generated reports, imported PGNs, engine paths and local config stay on your machine.

Source: https://github.com/Snowslash/chess-coach

## Interfaces

- CLI for scripting and technical use.
- Local web GUI served by FastAPI on `127.0.0.1` by default.
- Electron desktop GUI prototype under `apps/desktop/`.

The safe workflow is: import public games, analyse locally, export annotated PGN, review it yourself, then manually import into Lichess if wanted. Automatic Study helpers exist as explicit CLI actions only.

## What it does

- Parses PGN files.
- Identifies the target player’s colour.
- Analyses that player’s moves when the player is known.
- Uses Stockfish for tactical/evaluation signals when configured.
- Falls back to mock analysis for smoke tests if Stockfish is unavailable.
- Optionally adds Maia human-likeness context when Maia is installed and enabled.
- Imports public Lichess games by username.
- Exports annotated PGN comments from existing analysis JSON.
- Writes local Markdown reports, JSON bundles and annotated PGNs.

## Requirements

- Python 3.11+
- `python-chess` from this package’s dependencies — this is the Python library, not the PyChess GUI.
- Optional but recommended: `uv`.
- Optional: local Stockfish binary
- Optional: local Maia runtime/model weights
- Optional for the desktop GUI: Node.js 20+ and npm

Stockfish and Maia assets are not vendored in this repository.

## Install

```bash
git clone https://github.com/Snowslash/chess-coach.git
cd chess-coach
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

With Maia support:

```bash
python -m pip install -e '.[dev,maia2]'
```

## Install Stockfish

Stockfish is the tactical evaluator. It is GPL-3.0 and is not vendored in this repository. Install it from your operating-system package manager or from https://stockfishchess.org/download/, then point `STOCKFISH_PATH` at the binary.

## Configure local runtime

Copy the example environment file:

```bash
cp .env.example .env.stockfish
```

`.env.stockfish` is ignored by git. Keep tokens, local paths, PGNs and generated reports out of commits.

Common settings:

```bash
STOCKFISH_PATH=/usr/games/stockfish
STOCKFISH_DEPTH=12
STOCKFISH_TIME_LIMIT=0.1
CHESS_COACH_PLAYER=your_lichess_username
CHESS_COACH_PGN=input/lichess_recent_your_lichess_username.pgn
CHESS_COACH_OUT=reports/lichess_recent.md
MAIA2_ENABLED=true
MAIA2_GAME_TYPE=rapid
MAIA2_DEVICE=cpu
MAIA2_TARGET_ELO=1500
```

`LICHESS_TOKEN` is optional for public username imports. If used, keep it local. The web/desktop GUIs only send it to `lichess.org` for explicit Lichess actions.

## Local web GUI

Run the loopback-only web GUI:

```bash
python -m chess_coach web --host 127.0.0.1 --port 8765 --open
```

Or use the wrapper:

```bash
python3 scripts/run_web_gui.py
```

Open `http://127.0.0.1:8765/` if the browser does not open automatically.

The web GUI can:

- read/write `.env.stockfish`
- validate config fields
- test Stockfish and Maia readiness
- test Lichess username/token access
- import public Lichess games
- run local analysis
- export annotated PGN
- create a local diagnostic bundle

It deliberately does not provide a hosted backend, telemetry, automatic Study upload, no dashboard service or a packaged one-click installer. Automatic Study upload is planned later, but this web GUI is local-only by default.

## Desktop GUI

```bash
cd apps/desktop
npm install
npm run start
```

The desktop GUI uses the same local config and privacy boundary as the web GUI.

## CLI examples

Import recent public Lichess games:

```bash
python -m chess_coach import-lichess   --user your_lichess_username   --max 20   --out input/lichess_recent_your_lichess_username.pgn
```

Analyse games:

```bash
python -m chess_coach analyse   --pgn input/lichess_recent_your_lichess_username.pgn   --out reports/lichess_recent.md   --player your_lichess_username   --update-state
```

Export annotated PGN:

```bash
python -m chess_coach export-annotated-pgn   --from reports/lichess_recent.json   --out reports/annotated/lichess_recent.pgn   --max-games 10   --critical-only
```

Repeated local run:

```bash
bash scripts/run_report.sh
```

The script prints a compact summary including `stockfish_available`, `maia2_enabled`, `maia2_available`, and `maia2_reason`.

## Command quick reference

These one-line examples are intentionally easy to copy and are mirrored by the longer examples above:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --out input/lichess_recent_your_lichess_username.pgn
python -m chess_coach analyse --pgn input/lichess_recent_your_lichess_username.pgn --out reports/lichess_recent.md --player your_lichess_username --update-state
python -m chess_coach export-annotated-pgn --from reports/lichess_recent.json --out reports/annotated/latest.pgn --max-games 10 --critical-only
```

## v1 longitudinal workflow

```bash
python -m chess_coach cards --from reports/lichess_recent.json --out reports/cards/latest_cards.md
python -m chess_coach training-plan --from reports/lichess_recent.json --out reports/training_plan.md
python -m chess_coach weekly-review --out reports/weekly_review.md
bash scripts/run_weekly_review.sh
```

## Explicit Lichess Study helpers

Study creation/import is opt-in CLI work, not part of the main GUI workflow. Create a dedicated OAuth token with only the `study:write` scope, keep it in `.env.stockfish`, then run the helper commands deliberately.

Create a private Study:

```bash
python -m chess_coach lichess-study-create   --name "Chess Coach Review"   --visibility private   --token-env LICHESS_TOKEN
```

Import annotated PGN into that Study:

```bash
python -m chess_coach lichess-study-import   --study-id abc123   --pgn reports/annotated/lichess_recent.pgn   --orientation white   --token-env LICHESS_TOKEN
```

Semantics: `private` and `unlisted` are supported; public support intentionally absent. The helper appends chapters; it does not edit original Lichess games or auto-publish anything.

## Outputs and ignored local state

Typical outputs:

```text
reports/latest.md
reports/latest.json
reports/annotated/latest.pgn
reports/cards/latest_cards.md
reports/cards/latest_cards.json
reports/cards/lichess_recent_cards.md
reports/training_plan.md
reports/weekly_review.md
```

Generated reports, imported PGNs, `.coach/state.json`, `.env.stockfish`, engine binaries, Maia model weights, ignored local coaching state and desktop dependencies are ignored by default.

## Verify

Python tests:

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

Before publishing changes, check ignored local artefacts:

```bash
git status --ignored
git check-ignore -v .env.stockfish maia2_models/rapid_model.pt reports/lichess_recent.json input/lichess_recent_your_lichess_username.pgn apps/desktop/node_modules
```

## Licence

GPL-3.0-or-later. See `LICENSE` and `docs/licensing.md`.

This project depends on `python-chess`, which is GPL-3.0-or-later. Stockfish is GPL-3.0 and is invoked as a user-installed local UCI engine; it is not vendored here. Maia 2 is MIT-licensed, but Maia model weights/assets remain local runtime artefacts and are not committed.
