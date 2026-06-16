import json
from pathlib import Path

from chess_coach.cli import main



def test_v1_mock_workflow_end_to_end(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MAIA2_ENABLED", "false")
    sample_pgn = Path(__file__).resolve().parents[1] / "input" / "sample_games.pgn"
    state_path = tmp_path / "coach_state.json"
    report_path = tmp_path / "latest.md"
    report_json_path = tmp_path / "latest.json"
    cards_path = tmp_path / "cards.md"
    training_plan_path = tmp_path / "training_plan.md"
    weekly_review_path = tmp_path / "weekly_review.md"

    analyse_code = main(
        [
            "analyse",
            "--pgn",
            str(sample_pgn),
            "--out",
            str(report_path),
            "--player",
            "TestPlayer",
            "--mock",
            "--update-state",
            "--state-path",
            str(state_path),
        ]
    )
    assert analyse_code == 0
    assert report_path.exists()
    assert report_json_path.exists()
    assert state_path.exists()
    assert "# Chess Coach Report" in report_path.read_text(encoding="utf-8")
    report_bundle = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert report_bundle["source_pgn"].endswith("input/sample_games.pgn")
    assert report_bundle["metadata"]["mock_requested"] is True

    cards_code = main(["cards", "--from", str(report_json_path), "--out", str(cards_path)])
    assert cards_code == 0
    assert cards_path.exists()
    assert "# Chess Coach Review Cards" in cards_path.read_text(encoding="utf-8")

    training_code = main(["training-plan", "--from", str(report_json_path), "--out", str(training_plan_path)])
    assert training_code == 0
    assert training_plan_path.exists()
    assert "# Chess Coach Training Plan" in training_plan_path.read_text(encoding="utf-8")

    weekly_code = main(["weekly-review", "--state-path", str(state_path), "--out", str(weekly_review_path)])
    assert weekly_code == 0
    assert weekly_review_path.exists()
    weekly_text = weekly_review_path.read_text(encoding="utf-8")
    assert "# Chess Coach Weekly Review" in weekly_text
    assert "## Opening notes" in weekly_text

    state_data = json.loads(state_path.read_text(encoding="utf-8"))
    assert state_data["games"]
    assert state_data["runs"]
