from chess_coach.models import AnalysisBundle, CriticalMoment, GameAnalysis, PatternSummary
from chess_coach.position_export import lichess_analysis_url, render_position_exports


def test_lichess_analysis_url_encodes_fen_for_board_editor_import():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    url = lichess_analysis_url(fen)

    assert url.startswith("https://lichess.org/analysis/standard/")
    assert " " not in url
    assert "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR" in url
    assert url.endswith("?color=white")


def test_lichess_analysis_url_can_orient_black_review_positions():
    fen = "r2qkbnr/pp3ppp/4p3/3pPb2/3Q1B2/8/PPP1BPPP/RN3RK1 b kq - 0 9"

    url = lichess_analysis_url(fen, color="black")

    assert url.endswith("?color=black")


def test_render_position_exports_lists_reviewable_critical_moments():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    bundle = AnalysisBundle(
        source_pgn="input/game.pgn",
        games=[
            GameAnalysis(
                game_id="g1",
                event="Training",
                date="2026.05.30",
                critical_moments=[
                    CriticalMoment(
                        game_id="g1",
                        move_number=5,
                        side="black",
                        san="e6",
                        phase="opening",
                        fen_before=fen,
                        eval_change=-1.02,
                        classification="mistake",
                        best_move="f5g6",
                    )
                ],
            )
        ],
        patterns=PatternSummary(games_analysed=1, critical_moments=1),
    )

    markdown = render_position_exports(bundle)

    assert "## Reviewable position exports" in markdown
    assert "### 1. Training — move 5 black `e6`" in markdown
    assert f"- FEN: `{fen}`" in markdown
    assert "- Played: `e6`" in markdown
    assert "- Best move: `f5g6`" in markdown
    assert "- Eval change: `-1.02`" in markdown
    assert "- Lichess analysis:" in markdown
    assert "?color=black" in markdown
