# Chess Coach runtime

Chess Coach is still local-first. The difference now is interface choice:

- CLI for technical and scripted use
- local web GUI for Windows-native and non-terminal use
- Electron desktop GUI prototype/wrapper

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
- `python -m chess_coach web ...`
- `bash scripts/run_report.sh`
- `bash scripts/run_weekly_review.sh`
- the local web GUI
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

Web operations resolve input/output paths against the app's `project_root`, not
the process working directory. Analysis loads and validates the app's selected
`env_file` once per operation and passes that config snapshot to the pipeline;
it does not reload `.env.stockfish` from an unrelated current directory.
Existing environment-over-file precedence is unchanged, including when the
selected file is absent; invalid environment values reject analysis before
engine calls or report writes. Relative Stockfish file paths are rooted in
`project_root`; bare commands can still use `PATH`. Optional Maia loads receive
an explicit absolute `project_root/maia2_models` cache path, independent of the
launch directory or the selected config file's directory. CLI calls without an
explicit cache context retain Maia's `./maia2_models` default. Enabling Maia can
still download missing weights; loader failures remain visible in report
metadata without preventing the base analysis report.
API output paths remain project-relative, with symlinks resolved inside that
root. The derived JSON report is subject to the same confinement check.
Two operations with different roots/settings can overlap without changing cwd.
Operations targeting the same output filenames are not serialized: choose
distinct report paths if you want to retain both results.

## Local web GUI run

This is the preferred dev-mode path for Windows-native users in this slice.

From the repository root:

```bash
python3 -m chess_coach web --host 127.0.0.1 --port 8765 --open
```

Or:

```bash
python3 scripts/run_web_gui.py
```

If you skip `--open`, browse to:

```text
http://127.0.0.1:8765/
```

Local web GUI capabilities in this slice:

- load/save `.env.stockfish`
- inline validation
- first-run defaults
- Stockfish readiness test
- Maia readiness test
- Lichess username/token probe
- public Lichess PGN import by username
- local analysis
- annotated PGN export
- local diagnostic bundle

Local web privacy boundary:

- Binds to `127.0.0.1` by default
- Refuses non-loopback hosts unless `--allow-lan` is passed explicitly
- Your Lichess token is only sent to lichess.org
- Generated reports and PGNs stay on this machine
- Review the PGN before importing it into Lichess

Windows notes:

- No WSL is required for the intended user path
- Install Stockfish on Windows, then paste the `stockfish.exe` path into the UI
- A packaged one-click `.exe` remains future work after the local web GUI is stable

## Desktop GUI run

From the repository root:

```bash
cd apps/desktop
npm install
npm run start
```

Desktop behaviour in this slice:

- starts the same loopback FastAPI application and loads the canonical React UI;
- uses the same HTTP settings, readiness, Lichess import, analysis, export and diagnostics workflows as browser mode;
- exposes only constrained native file picking, project-local output opening and allowlisted HTTPS external URLs;
- does not expose config, token, import, analysis, export or diagnostics business operations through Electron IPC;
- remains a source/development thin shell that requires a local Python/Chess Coach runtime; no standalone Windows installer is claimed.

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

## PGN starting positions

Parsing, mock/Stockfish analysis and annotated PGN export share one
standard-chess starting-position contract: use the `FEN` header when present,
otherwise use the ordinary initial position. As in python-chess, a FEN is
honoured even when `SetUp` is absent. Move numbers and sides come from the board,
including Black-to-move setups with a non-default fullmove number. Export keeps
authored `FEN`, `SetUp` and standard-variant headers (adding `SetUp=1` only if a
FEN lacks it). Non-standard variants, including Chess960 castling positions,
are rejected explicitly rather than analysed as ordinary chess.

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

History still changes only when explicitly requested with `analyse --update-state`.
`save_state` writes the existing schema to a private, same-directory temporary
file, flushes and fsyncs it, then atomically replaces the destination. Serialization,
write, sync or replacement errors propagate to the caller; before replacement,
the previous file stays readable and unchanged. Handled failures clean up the
temporary file. Reports already produced by analysis may remain if a later
history save fails; no successful history update is reported in that case.
This is snapshot publication, not a lock or merge across competing writers.
Avoid concurrent read/update/save cycles for the same history. An abrupt process
kill may leave a temporary file; directory-entry durability after power loss is
not guaranteed. There is no schema migration, database or automatic history update.

## Runtime boundary

- Stockfish remains the tactical truth layer.
- Maia 2 remains optional human-likeness annotation.
- If Maia is unavailable, the Stockfish/mock workflow remains usable.
- The local web GUI is still local-only; there is no hosted dashboard, no dashboard service, and no remote backend in this repository.
- Electron remains preserved as a separate local wrapper path.

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
