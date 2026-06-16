import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run_report_script_uses_existing_runtime_without_installing():
    script = Path("scripts/run_report.sh")
    assert script.exists(), "Expected a stable run script for using the existing local runtime"
    text = script.read_text(encoding="utf-8")

    assert "CHESS_COACH_VENV" in text
    assert ".env.stockfish" in text
    assert "-m chess_coach analyse" in text
    assert "Chess Coach summary" in text
    assert "stockfish_available" in text
    assert "maia2_reason" in text
    assert "pip install" not in text
    assert "uv sync" not in text


def test_run_weekly_review_script_exists_and_has_expected_pipeline_steps():
    script = ROOT / "scripts/run_weekly_review.sh"
    assert script.exists(), "Expected a stable wrapper for the v1 longitudinal workflow"
    text = script.read_text(encoding="utf-8")

    assert "${CHESS_COACH_VENV:-$HOME/.venvs/chess-coach}" in text
    assert ".env.stockfish" in text
    assert "source .env.stockfish" in text
    assert "-m chess_coach import-lichess" in text
    assert "-m chess_coach analyse --pgn \"$PGN\" --out \"$REPORT\" --player \"$USER_NAME\" --update-state" in text
    assert "-m chess_coach cards --from \"${REPORT%.md}.json\" --out \"$CARDS\"" in text
    assert "-m chess_coach training-plan --from \"${REPORT%.md}.json\" --out \"$PLAN\"" in text
    assert "-m chess_coach weekly-review --out \"$WEEKLY\"" in text



def test_run_weekly_review_script_has_valid_bash_syntax():
    script = ROOT / "scripts/run_weekly_review.sh"
    result = subprocess.run(["bash", "-n", str(script)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr



def test_runtime_guide_documents_separate_setup_and_run_paths():
    guide = Path("docs/runtime.md")
    assert guide.exists(), "Expected runtime guide documenting persistent local deps"
    text = guide.read_text(encoding="utf-8")

    assert "one-time setup" in text.lower()
    assert "normal run" in text.lower()
    assert "maia2_models/" in text
    assert ".env.stockfish" in text
    assert "do not commit" in text.lower()
