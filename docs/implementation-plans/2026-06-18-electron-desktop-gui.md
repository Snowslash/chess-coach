# 2026-06-18 Electron desktop GUI for Chess Coach

## Goal

Implement one coherent local-first desktop slice so a non-technical user can:

1. open Chess Coach as a desktop app
2. configure settings without editing files
3. test Stockfish / Maia / Lichess readiness
4. import recent public Lichess games by username
5. analyse locally with the existing Python engine
6. export annotated PGN for manual Lichess use

## Scope kept in this slice

- Electron desktop app under `apps/desktop/`
- shared `.env.stockfish` config with the CLI
- inline validation
- settings export/import
- local diagnostic bundle
- log streaming from privileged process to renderer
- no hosted backend
- no telemetry
- no automatic Lichess Study upload in the main GUI loop

## Architecture

### Python remains the analysis engine

- keep `chess_coach` package and CLI as the source of truth for chess logic
- add `chess_coach/gui_support.py` for GUI-facing config, validation, readiness, Lichess probe, and diagnostic helpers
- preserve CLI backward compatibility with `.env.stockfish`

### Electron shell

- `src/main.js`: privileged bridge, file dialogs, subprocess execution, log redaction
- `src/preload.js`: narrow IPC surface via `contextBridge`
- `src/renderer/*`: plain HTML/CSS/JS utility UI
- renderer never shells out directly
- subprocesses use `spawn(..., argsArray, { shell: false })`

## Config surface

Expose these in the GUI:

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

Maia GUI constraints:

- game type options: `rapid`, `blitz`, `bullet`, `classical`
- target Elo dropdown: `1100..1900` by 100s
- device suggestions: `cpu`, `cuda`, `mps`; unknown values warn rather than crash

## Validation plan

Renderer and Python both validate:

- safe Lichess username characters
- positive Stockfish depth and time limit in bounded ranges
- Maia game type and Elo membership
- absolute-path warnings for portability-sensitive paths
- token redaction in exports, diagnostics, and logs

## Readiness plan

- Stockfish: configured path or PATH probe, then UCI handshake
- Maia: existing `maia2_available(config)` without triggering weight download
- Lichess: public `https://lichess.org/api/user/<username>` probe, optional Authorization header only to `lichess.org`

## Workflow plan

Primary screen: “Analyse my games”

- import recent games -> `python -m chess_coach import-lichess ...`
- analyse games -> `python -m chess_coach analyse ... --update-state`
- export annotated PGN -> `python -m chess_coach export-annotated-pgn ...`

## Diagnostics plan

Write local bundles under `.coach/diagnostics/` with:

- app/package/git metadata
- Python executable/version
- redacted config
- package/import status
- readiness summary
- redacted recent logs
- optional inclusion of current PGN and current report only when explicitly requested

## Verification plan

- Python tests for config roundtrip, validation, token redaction, Lichess probe, diagnostic bundle
- Node tests for validation helpers and argument-array command builders
- full Python suite
- `npm test`
- `npm run build` static syntax/build check for the Electron app
- local smoke for config load/save, CLI compatibility, readiness JSON, and command construction

## Known boundary

This agent environment can implement and statically verify the desktop app, but visual Electron window smoke on the real Windows desktop may still need host-side confirmation with:

```bash
cd apps/desktop
npm install
npm run start
```
