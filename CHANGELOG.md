# Changelog

All notable changes to Chess Coach are documented here.

## [Unreleased]

### Added

- Local `export-annotated-pgn` CLI for converting existing analysis JSON into parseable annotated PGN.
- `chess_coach.annotated_pgn` renderer that reconstructs legal move order with `python-chess` and attaches concise `Chess Coach:` comments to critical moments.
- Ignore hygiene for generated annotated PGNs under `reports/annotated/*.pgn`.

### Documented

- Local annotated PGN export example and privacy note that generated annotated PGNs stay local and ignored.
- This slice requires no token and no network.
- Lichess Study API create/import is planned later and not part of this slice.

### Possible v2 direction

- Next likely v2 step: add optional private/unlisted Lichess Study create/import commands after the local annotated PGN export has proven useful. A local GUI remains a later fallback if Study export is too constrained.

## [1.0.0] - 2026-06-06

### Added

- Local longitudinal coach state under ignored `.coach/` storage.
- Repeated-run history tracking for analysed games, patterns and coach runs.
- Review card generation from critical moments, with Markdown export and CLI support.
- Weekly coach review generation with trend summaries, aggregate direction and Markdown export.
- Measurable training-plan generation linked to patterns, review cards and critical moments.
- Lichess import filters for performance type, rated-only games and recent-day windows.
- De-duplication helper for already analysed games in coach history.
- Lightweight opening-family extraction from SAN move prefixes.
- Opening-family notes in history and weekly review output.
- `scripts/run_weekly_review.sh` for the default v1 workflow.
- End-to-end mock v1 workflow coverage using temp paths and no engine/model/network dependency.

### Documented

- v1 longitudinal workflow in README and runtime docs.
- Local-only, CLI-first privacy boundary: no dashboard, no web app and no hosted service in v1.
- Ignored local artifacts: `.coach/`, imported personal PGNs, generated reports, review cards, training plans, env files and model files.
- Runtime boundary between Stockfish tactical analysis and optional Maia2 human-likeness annotation.

### Verified

- Docker/mock release-readiness audit passed.
- Real WSL/host wrapper smoke passed with Stockfish and recent Lichess import.
- Maia2 host smoke passed with the full recent-game set.
- Generated/private artifacts remained ignored and uncommitted.
