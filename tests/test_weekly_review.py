from datetime import datetime

from chess_coach.history import CoachState, GameHistoryEntry, PatternHistoryEntry, RunHistoryEntry


def make_state() -> CoachState:
    games = {
        f"lichess:{index}": GameHistoryEntry(
            key=f"lichess:{index}",
            game_id=str(index),
            site=f"https://lichess.org/{index}",
            date="2026.06.04",
            white="TestPlayer",
            black=f"Opponent{index}",
            result="1-0",
            critical_moments=2 if index < 3 else 1,
            opening_family="e4 e5 Nf3 Nc6 Bc4" if index in {0, 1} else ("d4 d5 c4" if index == 2 else None),
        )
        for index in range(10)
    }
    patterns = {
        "middlegame_tactics": PatternHistoryEntry(
            pattern_id="middlegame_tactics",
            label="Middlegame tactics",
            occurrences=6,
            trend="worsening",
        ),
        "endgame_conversion": PatternHistoryEntry(
            pattern_id="endgame_conversion",
            label="Endgame conversion",
            occurrences=4,
            trend="stable",
        ),
        "opening_discipline": PatternHistoryEntry(
            pattern_id="opening_discipline",
            label="Opening discipline",
            occurrences=2,
            trend="improving",
        ),
    }
    runs = [
        RunHistoryEntry(
            run_id="run-1",
            generated_at=datetime(2026, 6, 1, 9, 0, 0),
            source_pgn="input/older_games.pgn",
            game_keys=[f"lichess:{index}" for index in range(7)],
            games_analysed=7,
            critical_moments=14,
            top_patterns=["Middlegame tactics", "Endgame conversion"],
        ),
        RunHistoryEntry(
            run_id="run-2",
            generated_at=datetime(2026, 6, 8, 9, 0, 0),
            source_pgn="input/latest_games.pgn",
            game_keys=[f"lichess:{index}" for index in range(7, 10)],
            games_analysed=3,
            critical_moments=3,
            top_patterns=["Middlegame tactics", "Opening discipline"],
        ),
    ]
    return CoachState(games=games, patterns=patterns, runs=runs)


def make_state_without_pattern_trends(*, previous_critical_moments: int, latest_critical_moments: int, latest_games: int = 3) -> CoachState:
    games = {
        f"lichess:{index}": GameHistoryEntry(
            key=f"lichess:{index}",
            game_id=str(index),
            site=f"https://lichess.org/{index}",
            date="2026.06.04",
            white="TestPlayer",
            black=f"Opponent{index}",
            result="1-0",
        )
        for index in range(6)
    }
    runs = [
        RunHistoryEntry(
            run_id="run-1",
            generated_at=datetime(2026, 6, 1, 9, 0, 0),
            source_pgn="input/older_games.pgn",
            game_keys=[f"lichess:{index}" for index in range(3)],
            games_analysed=3,
            critical_moments=previous_critical_moments,
            top_patterns=["Middlegame tactics"],
        ),
        RunHistoryEntry(
            run_id="run-2",
            generated_at=datetime(2026, 6, 8, 9, 0, 0),
            source_pgn="input/latest_games.pgn",
            game_keys=[f"lichess:{index}" for index in range(3, 6)],
            games_analysed=latest_games,
            critical_moments=latest_critical_moments,
            top_patterns=["Middlegame tactics"],
        ),
    ]
    return CoachState(games=games, runs=runs)


def test_weekly_review_summarises_recent_run_against_state():
    from chess_coach.weekly_review import build_weekly_review

    review = build_weekly_review(make_state())

    assert review.games_analysed == 3
    assert review.total_known_games == 10
    assert review.critical_moments == 3
    assert review.top_patterns == ["Middlegame tactics", "Opening discipline"]
    assert review.improved == ["Opening discipline"]
    assert review.worsened == ["Middlegame tactics"]
    assert review.stable == ["Endgame conversion"]
    assert review.latest_critical_moments_per_game == 1.0
    assert review.previous_critical_moments_per_game == 2.0
    assert review.aggregate_trend == "improving"
    assert "2.00 to 1.00" in review.aggregate_trend_note
    assert review.opening_notes == [
        "e4 e5 Nf3 Nc6 Bc4: 4 critical moments across 2 games",
        "d4 d5 c4: 2 critical moments across 1 game",
    ]
    assert review.uncertainty_notes == []


def test_weekly_review_reports_no_history_when_state_empty():
    from chess_coach.weekly_review import build_weekly_review

    review = build_weekly_review(CoachState())

    assert review.games_analysed == 0
    assert review.total_known_games == 0
    assert review.aggregate_trend == "unknown"
    assert "No coach history" in review.uncertainty_notes[0]


def test_weekly_review_uses_run_history_to_report_improving_without_pattern_trends():
    from chess_coach.weekly_review import build_weekly_review, weekly_review_markdown

    review = build_weekly_review(make_state_without_pattern_trends(previous_critical_moments=6, latest_critical_moments=3))
    markdown = weekly_review_markdown(review)

    assert review.aggregate_trend == "improving"
    assert review.improved == []
    assert review.worsened == []
    assert review.stable == []
    assert review.latest_critical_moments_per_game == 1.0
    assert review.previous_critical_moments_per_game == 2.0
    assert "fewer critical moments per game" in markdown.lower()
    assert "2.00 to 1.00" in markdown
    assert "No reliable trend change is available yet." not in markdown


def test_weekly_review_uses_run_history_to_report_worsening_without_pattern_trends():
    from chess_coach.weekly_review import build_weekly_review, weekly_review_markdown

    review = build_weekly_review(make_state_without_pattern_trends(previous_critical_moments=3, latest_critical_moments=6))
    markdown = weekly_review_markdown(review)

    assert review.aggregate_trend == "worsening"
    assert review.latest_critical_moments_per_game == 2.0
    assert review.previous_critical_moments_per_game == 1.0
    assert "more critical moments per game" in markdown.lower()
    assert "1.00 to 2.00" in markdown
    assert "No reliable trend change is available yet." not in markdown


def test_weekly_review_distinguishes_zero_game_latest_run_from_no_history():
    from chess_coach.weekly_review import build_weekly_review, weekly_review_markdown

    review = build_weekly_review(make_state_without_pattern_trends(previous_critical_moments=3, latest_critical_moments=0, latest_games=0))
    markdown = weekly_review_markdown(review)

    assert review.aggregate_trend == "unknown"
    assert review.games_analysed == 0
    assert "No coach history is available yet" not in markdown
    assert "latest run contained 0 game(s)" in markdown
    assert "Cannot compare critical moments per game" in markdown


def test_weekly_review_markdown_has_required_sections_and_direct_language(tmp_path):
    from chess_coach.weekly_review import build_weekly_review, weekly_review_markdown, write_weekly_review_markdown

    review = build_weekly_review(make_state())

    markdown = weekly_review_markdown(review)

    assert "# Chess Coach Weekly Review" in markdown
    assert "## Executive diagnosis" in markdown
    assert "## What changed since last review" in markdown
    assert "## Top recurring leaks" in markdown
    assert "## Opening notes" in markdown
    assert "## This week’s training focus" in markdown
    assert "## Uncertainty" in markdown
    assert "Middlegame tactics" in markdown
    assert "e4 e5 Nf3 Nc6 Bc4: 4 critical moments across 2 games" in markdown
    assert "Analysed 3 game(s) in the latest run" in markdown
    assert "critical moments per game improved from 2.00 to 1.00" in markdown

    out_path = tmp_path / "weekly_review.md"
    written = write_weekly_review_markdown(review, out_path)

    assert written == out_path
    assert out_path.read_text(encoding="utf-8") == markdown
