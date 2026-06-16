from datetime import datetime
from pathlib import Path

import chess.pgn

from chess_coach import cli
from chess_coach.history import CoachState, RunHistoryEntry
from chess_coach.models import AnalysisBundle, CriticalMoment, GameAnalysis, MoveAnalysis, PatternSummary


def make_moves() -> list[MoveAnalysis]:
    return [
        MoveAnalysis(
            move_number=1,
            side="white",
            san="e4",
            uci="e2e4",
            phase="opening",
            fen_before="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            eval_before=0.2,
            eval_after=0.1,
            eval_change=-0.1,
            best_move="d2d4",
            classification="inaccuracy",
            note="Playable, but gave up some central control.",
        ),
        MoveAnalysis(
            move_number=1,
            side="black",
            san="e5",
            uci="e7e5",
            phase="opening",
            fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            eval_before=0.1,
            eval_after=0.0,
            eval_change=-0.1,
            best_move="e7e5",
            classification="book/neutral",
        ),
        MoveAnalysis(
            move_number=2,
            side="white",
            san="Bc4",
            uci="f1c4",
            phase="opening",
            fen_before="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            eval_before=0.0,
            eval_after=0.2,
            eval_change=0.2,
            best_move="g1f3",
            classification="book/neutral",
        ),
        MoveAnalysis(
            move_number=2,
            side="black",
            san="Nc6",
            uci="b8c6",
            phase="opening",
            fen_before="rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2",
            eval_before=0.2,
            eval_after=0.0,
            eval_change=-0.2,
            best_move="g8f6",
            classification="book/neutral",
        ),
        MoveAnalysis(
            move_number=3,
            side="white",
            san="Qh5",
            uci="d1h5",
            phase="opening",
            fen_before="r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR w KQkq - 2 3",
            eval_before=0.0,
            eval_after=0.3,
            eval_change=0.3,
            best_move="g1f3",
            classification="book/neutral",
        ),
        MoveAnalysis(
            move_number=3,
            side="black",
            san="Nf6",
            uci="g8f6",
            phase="opening",
            fen_before="r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3",
            eval_before=0.3,
            eval_after=3.4,
            eval_change=3.1,
            best_move="g7g6",
            classification="blunder",
            note="Missed the mate threat on f7.",
            maia2_played_move_prob=0.07,
        ),
        MoveAnalysis(
            move_number=4,
            side="white",
            san="Qxf7#",
            uci="h5f7",
            phase="opening",
            fen_before="r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
            eval_before=3.4,
            eval_after=99.0,
            eval_change=95.6,
            best_move="h5f7",
            classification="book/neutral",
        ),
    ]


def make_bundle() -> AnalysisBundle:
    return AnalysisBundle(
        generated_at=datetime(2026, 6, 4, 12, 0, 0),
        source_pgn="input/sample_games.pgn",
        games=[
            GameAnalysis(
                game_id="abc",
                event="Training game",
                site="https://lichess.org/abc",
                date="2026.06.04",
                white="TestPlayer",
                black="Opponent",
                result="1-0",
                player_colour="white",
                headers={
                    "Event": "Training game",
                    "Site": "https://lichess.org/abc",
                    "Date": "2026.06.04",
                    "White": "TestPlayer",
                    "Black": "Opponent",
                    "Result": "1-0",
                },
                moves=make_moves(),
                critical_moments=[
                    CriticalMoment(
                        game_id="abc",
                        move_number=3,
                        side="black",
                        san="Nf6",
                        phase="opening",
                        fen_before="fen-1",
                        eval_change=3.1,
                        classification="blunder",
                        best_move="g7g6",
                        note="Missed the mate threat on f7.",
                    )
                ],
            )
        ],
        patterns=PatternSummary(
            games_analysed=1,
            critical_moments=1,
            recurring_weaknesses=["Middlegame tactics"],
            training_priorities=["Review middlegame tactical misses"],
        ),
    )


def test_cli_import_lichess_fetches_recent_games(tmp_path: Path, monkeypatch, capsys):
    calls = []

    def fake_fetch(username, out_path, max_games, perf=None, rated_only=False, since_days=None):
        calls.append((username, Path(out_path), max_games, perf, rated_only, since_days))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text('[Event "Game"]\n\n1. e4 *\n', encoding="utf-8")
        return Path(out_path)

    monkeypatch.setattr(cli, "fetch_recent_games", fake_fetch)
    out = tmp_path / "recent.pgn"

    code = cli.main(["import-lichess", "--user", "exampleuser", "--max", "3", "--out", str(out)])

    assert code == 0
    assert calls == [("exampleuser", out, 3, None, False, None)]
    assert f"Imported Lichess PGN: {out}" in capsys.readouterr().out



def test_cli_import_lichess_accepts_filter_arguments(tmp_path: Path, monkeypatch):
    calls = []

    def fake_fetch(username, out_path, max_games, perf=None, rated_only=False, since_days=None):
        calls.append((username, Path(out_path), max_games, perf, rated_only, since_days))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text('[Event "Game"]\n\n1. e4 *\n', encoding="utf-8")
        return Path(out_path)

    monkeypatch.setattr(cli, "fetch_recent_games", fake_fetch)
    out = tmp_path / "recent.pgn"

    code = cli.main([
        "import-lichess",
        "--user",
        "TestPlayer",
        "--max",
        "20",
        "--perf",
        "rapid",
        "--rated-only",
        "--since-days",
        "14",
        "--out",
        str(out),
    ])

    assert code == 0
    assert calls == [("TestPlayer", out, 20, "rapid", True, 14)]



def test_analyse_without_update_state_does_not_write_state(tmp_path: Path, monkeypatch, capsys):
    bundle = make_bundle()
    pgn = tmp_path / "sample.pgn"
    pgn.write_text('[Event "Game"]\n\n1. e4 *\n', encoding="utf-8")
    out = tmp_path / "report.md"
    state_path = tmp_path / ".coach" / "state.json"

    monkeypatch.setattr(cli, "analyse_pgn", lambda *args, **kwargs: bundle)

    code = cli.main(["analyse", "--pgn", str(pgn), "--out", str(out), "--state-path", str(state_path)])

    assert code == 0
    assert not state_path.exists()
    assert "Updated coach state:" not in capsys.readouterr().out



def test_analyse_with_update_state_writes_state(tmp_path: Path, monkeypatch, capsys):
    bundle = make_bundle()
    pgn = tmp_path / "sample.pgn"
    pgn.write_text('[Event "Game"]\n\n1. e4 *\n', encoding="utf-8")
    out = tmp_path / "report.md"
    state_path = tmp_path / ".coach" / "state.json"

    monkeypatch.setattr(cli, "analyse_pgn", lambda *args, **kwargs: bundle)

    code = cli.main(
        [
            "analyse",
            "--pgn",
            str(pgn),
            "--out",
            str(out),
            "--update-state",
            "--state-path",
            str(state_path),
        ]
    )

    assert code == 0
    assert state_path.exists()
    assert '"game_id": "abc"' in state_path.read_text(encoding="utf-8")
    assert f"Updated coach state: {state_path}" in capsys.readouterr().out



def test_cards_cli_writes_markdown_from_report_json(tmp_path: Path):
    json_path = tmp_path / "latest.json"
    out_path = tmp_path / "cards.md"
    json_path.write_text(make_bundle().model_dump_json(indent=2), encoding="utf-8")

    result = cli.main(["cards", "--from", str(json_path), "--out", str(out_path)])

    assert result == 0
    assert out_path.exists()
    assert "Review Cards" in out_path.read_text(encoding="utf-8")



def test_export_annotated_pgn_cli_writes_parseable_pgn(tmp_path: Path, capsys):
    json_path = tmp_path / "latest.json"
    out_path = tmp_path / "annotated" / "latest.pgn"
    json_path.write_text(make_bundle().model_dump_json(indent=2), encoding="utf-8")

    result = cli.main([
        "export-annotated-pgn",
        "--from",
        str(json_path),
        "--out",
        str(out_path),
        "--max-games",
        "1",
        "--critical-only",
    ])

    assert result == 0
    assert out_path.exists()
    with out_path.open(encoding="utf-8") as handle:
        game = chess.pgn.read_game(handle)
    assert game is not None
    assert game.headers["White"] == "TestPlayer"
    stdout = capsys.readouterr().out
    assert f"Annotated PGN: {out_path}" in stdout
    assert "Games exported: 1" in stdout



def test_export_annotated_pgn_cli_fails_clearly_when_json_is_missing(tmp_path: Path, capsys):
    missing = tmp_path / "missing.json"
    out_path = tmp_path / "annotated" / "latest.pgn"

    result = cli.main(["export-annotated-pgn", "--from", str(missing), "--out", str(out_path)])

    assert result == 2
    stderr = capsys.readouterr().err
    assert f"Analysis JSON not found: {missing}" in stderr
    assert not out_path.exists()


def test_export_annotated_pgn_cli_rejects_negative_max_games(tmp_path: Path, capsys):
    json_path = tmp_path / "latest.json"
    out_path = tmp_path / "annotated" / "latest.pgn"
    json_path.write_text(make_bundle().model_dump_json(indent=2), encoding="utf-8")

    result = cli.main([
        "export-annotated-pgn",
        "--from",
        str(json_path),
        "--out",
        str(out_path),
        "--max-games",
        "-1",
    ])

    assert result == 2
    stderr = capsys.readouterr().err
    assert "--max-games must be >= 0" in stderr
    assert not out_path.exists()



def test_weekly_review_cli_writes_markdown_from_state_json(tmp_path: Path):
    state_path = tmp_path / ".coach" / "state.json"
    out_path = tmp_path / "weekly_review.md"
    state = CoachState(
        runs=[
            RunHistoryEntry(
                run_id="run-1",
                generated_at=datetime(2026, 6, 8, 9, 0, 0),
                source_pgn="input/latest_games.pgn",
                game_keys=["lichess:abc"],
                games_analysed=1,
                critical_moments=1,
                top_patterns=["Middlegame tactics"],
            )
        ]
    )
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    result = cli.main(["weekly-review", "--state-path", str(state_path), "--out", str(out_path)])

    assert result == 0
    assert out_path.exists()
    assert "Weekly Review" in out_path.read_text(encoding="utf-8")



def test_training_plan_cli_writes_markdown_from_report_json(tmp_path: Path):
    json_path = tmp_path / "latest.json"
    out_path = tmp_path / "training_plan.md"
    json_path.write_text(make_bundle().model_dump_json(indent=2), encoding="utf-8")

    result = cli.main(["training-plan", "--from", str(json_path), "--out", str(out_path)])

    assert result == 0
    assert out_path.exists()
    assert "Training Plan" in out_path.read_text(encoding="utf-8")
