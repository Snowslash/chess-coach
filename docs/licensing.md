# Licensing and GitHub publishing

Chess Coach should be published as **GPL-3.0-or-later**.

This is not because Maia2 is restrictive. Maia2 is MIT-licensed. The practical reason is that this project directly depends on `python-chess`, which is GPL-3.0-or-later. Stockfish is also GPL-3.0, although this repository does not vendor Stockfish and only invokes a user-installed local UCI engine.

## Project license

- Repository license: `GPL-3.0-or-later`
- Full license text: `LICENSE`
- Python package metadata: `pyproject.toml`

## Third-party components

| Component | Role | Licence / handling |
|---|---|---|
| `python-chess` | Required PGN / board / engine interface dependency | GPL-3.0-or-later; drives the repo-level GPL choice. |
| Stockfish | Optional local tactical evaluator via UCI binary | GPL-3.0; not vendored here. Users install/configure it locally. |
| Maia2 package | Optional human-likeness context | MIT; optional Python dependency. |
| Maia2 model weights/assets | Optional local model runtime data | Do not vendor without separate source/licence review; keep under ignored local `maia2_models/`. |
| Generated reports / annotated PGNs / imported personal PGNs / local coach state | Local analysis artifacts | Ignored by default; commit only deliberate examples/fixtures. |

## Do not commit

```text
.env.stockfish
.env.* except .env.example/.env.sample
maia2_models/
stockfish/
engines/
models/
*.pt
*.pth
*.onnx
*.bin
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
.venv/
*.egg-info/
__pycache__/
*.pyc
```

## Safe to commit

```text
LICENSE
README.md
docs/
chess_coach/
scripts/
tests/
pyproject.toml
uv.lock
.env.example
input/sample_games.pgn
reports/.gitkeep
```

## Pre-push checklist

Before creating/pushing the GitHub repo:

```bash
git status --ignored
git check-ignore -v .env.stockfish maia2_models/rapid_model.pt reports/lichess_recent_maia2.json input/lichess_recent_your_lichess_username.pgn
git add --dry-run .
python -m pytest -q
```

Expected result: runtime artifacts, generated reports, local env files, model weights, and imported personal PGNs are ignored and not staged.
