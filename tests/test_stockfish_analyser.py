from chess_coach.config import ChessCoachConfig
from chess_coach.models import ParsedGame, ParsedMove
from chess_coach.stockfish_analyser import analyse_game_mock


STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
AFTER_E4_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"


def test_mock_analysis_records_fen_before_each_move():
    parsed = ParsedGame(
        game_id="g1",
        moves=[
            ParsedMove(move_number=1, side="white", san="e4", uci="e2e4"),
            ParsedMove(move_number=1, side="black", san="e5??", uci="e7e5"),
        ],
    )

    analysis = analyse_game_mock(parsed)

    assert analysis.moves[0].fen_before == STARTING_FEN
    assert analysis.moves[1].fen_before == AFTER_E4_FEN
    assert analysis.critical_moments[0].fen_before == AFTER_E4_FEN


def test_mock_analysis_only_exports_player_colour_critical_moments_when_known():
    parsed = ParsedGame(
        game_id="g1",
        player_colour="white",
        moves=[
            ParsedMove(move_number=1, side="white", san="e4??", uci="e2e4"),
            ParsedMove(move_number=1, side="black", san="e5??", uci="e7e5"),
        ],
    )

    analysis = analyse_game_mock(parsed)

    assert [m.side for m in analysis.critical_moments] == ["white"]
    assert analysis.critical_moments[0].san == "e4??"
