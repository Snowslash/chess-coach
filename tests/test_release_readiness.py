import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_walks_new_user_through_dependencies_setup_import_and_run():
    readme = text("README.md")
    required_phrases = [
        "python-chess",
        "not the PyChess GUI",
        "Install Stockfish",
        "python -m pip install -e '.[dev,maia2]'",
        "python -m chess_coach import-lichess --user",
        "python -m chess_coach analyse --pgn",
        "bash scripts/run_report.sh",
        "MAIA2_ENABLED=true",
        "maia2_reason",
        "## v1 longitudinal workflow",
        "--update-state",
        ".coach/state.json",
        "weekly-review",
        "training-plan",
        "scripts/run_weekly_review.sh",
        "export-annotated-pgn",
        "reports/annotated/latest.pgn",
        "planned later",
        "no token",
        "no network",
        "no dashboard",
        "local-only",
    ]
    for phrase in required_phrases:
        assert phrase in readme



def test_github_hygiene_docs_explain_local_artifacts_and_licensing():
    readme = text("README.md")
    runtime = text("docs/runtime.md")
    licensing = text("docs/licensing.md")
    gitignore = text(".gitignore")
    env_example = text(".env.example")

    example_private_username = "PrivateUser123"
    example_private_windows_path = "C:\\Users\\PrivateUser123"
    for forbidden in [example_private_username, "/usr/games/stockfish", example_private_windows_path]:
        assert forbidden not in env_example
    for public_doc in [readme, runtime]:
        assert example_private_username not in public_doc
        assert example_private_windows_path not in public_doc

    for pattern in [
        ".env.*",
        "!.env.example",
        "maia2_models/",
        "*.pt",
        "reports/*.json",
        "reports/**/*.json",
        "reports/*.md",
        "reports/**/*.md",
        "reports/annotated/*.pgn",
        "input/lichess_recent*.pgn",
        ".coach/",
        "*.coach.json",
        "dist/",
        "build/",
        "!input/sample_games.pgn",
    ]:
        assert pattern in gitignore

    for path in [
        "reports/latest.md",
        "reports/latest.json",
        "reports/cards/latest_cards.md",
        "reports/cards/latest_cards.json",
        "reports/annotated/latest.pgn",
    ]:
        result = subprocess.run(
            ["git", "check-ignore", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"expected ignored path: {path}"

    sample_result = subprocess.run(
        ["git", "check-ignore", "input/sample_games.pgn"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert sample_result.returncode == 1, "expected committed sample fixture to remain unignored"

    assert ".coach/" in readme or ".coach/" in runtime
    assert ".coach/state.json" in readme or ".coach/state.json" in runtime
    assert "ignored local coaching state" in readme.lower() or "ignored local coaching state" in runtime.lower()
    for phrase in [
        "--update-state",
        "weekly-review",
        "cards",
        "training-plan",
        "scripts/run_weekly_review.sh",
        "export-annotated-pgn",
        "reports/annotated/latest.pgn",
        "annotated PGN",
        "local-only",
        "planned later",
        "no token",
        "no network",
    ]:
        assert phrase in readme or phrase in runtime
    assert "no dashboard" in readme.lower() or "no dashboard" in runtime.lower()

    for document in [readme, licensing]:
        assert "GPL-3.0-or-later" in document
        assert "python-chess" in document
        assert "Stockfish" in document
        assert "not vendored" in document
        assert "Maia" in document
        assert "model weights" in document
