# Chess Coach runtime

Chess Coach is still local-first. The difference now is interface choice:

- CLI for technical and scripted use
- Electron desktop GUI for non-technical users

There is still no hosted service, no analytics, and no data sent to Sangeev.

## One-time setup

From WSL:

```bash
cd "/mnt/c/Users/<you>/Documents/Coding Projects/chess-coach"
bash scripts/setup_wsl.sh
```

That creates or refreshes a WSL-native virtual environment at:

```text
$HOME/.venvs/chess-coach
```

Keep the venv out of the Windows-mounted project folder.

## Local dependencies

Install the Python project with:

```bash
python -m pip install -e '.[dev,maia2]'
```

Install Stockfish locally and point `.env.stockfish` at the binary. Keep `.env.stockfish` local; do not commit it.

Keep Maia packages and model files local too. `maia2_models/` stays ignored.

## Shared local config

Copy the template once:

```bash
cp .env.example .env.stockfish
```

That file is shared by:

- `python -m chess_coach ...`
- `bash scripts/run_report.sh`
- `bash scripts/run_weekly_review.sh`
- the Electron desktop GUI

Typical values:

```bash
export STOCKFISH_PATH=/path/to/stockfish
export CHESS_COACH_PLAYER=your_lichess_username
export CHESS_COACH_PGN=input/lichess_recent_your_lichess_username.pgn
export CHESS_COACH_OUT=reports/lichess_recent.md
export MAIA2_ENABLED=true
export MAIA2_GAME_TYPE=rapid
export MAIA2_DEVICE=cpu
export MAIA2_TARGET_ELO=1500
```

`LICHESS_TOKEN` is optional for the default public-username import flow.

## Desktop GUI run

From the repository root:

```bash
cd apps/desktop
npm install
npm run start
```

Desktop capabilities in this slice:

- load/save `.env.stockfish`
- inline validation
- first-run defaults
- Stockfish readiness test
- Maia readiness test
- Lichess username/token probe
- public Lichess PGN import by username
- local analysis
- annotated PGN export
- settings export/import
- local diagnostic bundle

Desktop privacy boundary:

- Runs locally.
- Your Lichess token is only sent to lichess.org.
- Generated reports and PGNs stay on this machine.
- Review the PGN before importing it into Lichess.

## CLI import and analysis

Import public games:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --out input/lichess_recent_your_lichess_username.pgn
```

Or narrow the window:

```bash
python -m chess_coach import-lichess --user your_lichess_username --max 20 --perf rapid --rated-only --since-days 14 --out input/lichess_recent_your_lichess_username.pgn
```

Analyse locally:

```bash
python -m chess_coach analyse --pgn input/lichess_recent_your_lichess_username.pgn --out reports/lichess_recent.md --player your_lichess_username --update-state
```

Export annotated PGN:

```bash
python -m chess_coach export-annotated-pgn --from reports/lichess_recent.json --out reports/annotated/lichess_recent.pgn --max-games 10 --critical-only
```

## Normal run

After setup:

```bash
bash scripts/run_report.sh
```

For the broader local longitudinal flow:

```bash
bash scripts/run_weekly_review.sh
```

The wrappers read `.env.stockfish`, use the persistent venv, and print summary fields such as `stockfish_available`, `maia2_enabled`, `maia2_available`, and `maia2_reason`.

## Lichess Study helpers

Study creation/import remains explicit CLI-only in this slice.

```bash
python -m chess_coach lichess-study-create --name "Chess Coach Review 2026-06-18" --visibility private --token-env LICHESS_TOKEN
python -m chess_coach lichess-study-import --study-id abc123 --pgn reports/annotated/lichess_recent.pgn --orientation white --token-env LICHESS_TOKEN
```

Semantics:

- `private` and `unlisted` supported
- public support intentionally absent
- import appends chapters
- it does not edit original Lichess games

## Local state and outputs

These remain local ignored artifacts:

- `.env.stockfish`
- `.coach/`
- `.coach/state.json`
- `.coach/diagnostics/`
- imported personal PGNs
- generated reports
- generated annotated PGNs
- `maia2_models/`

## Runtime boundary

- Stockfish remains the tactical truth layer.
- Maia 2 remains optional human-likeness annotation.
- If Maia is unavailable, the Stockfish/mock workflow remains usable.
- There is no hosted dashboard and no browser-hosted web app in this repository; the GUI is a local desktop shell.

## Git / licence hygiene

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
apps/desktop/node_modules/
apps/desktop/dist/
apps/desktop/out/
input/lichess_recent*.pgn
input/lichess_pgn_*.pgn
```

The repository should contain integration code, docs, tests, and placeholder configuration only. Third-party engines, model weights, local env files, imported PGNs, and generated analysis artifacts stay local.
