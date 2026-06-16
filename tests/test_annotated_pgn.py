from __future__ import annotations

from io import StringIO

import chess.pgn

from chess_coach.models import AnalysisBundle, CriticalMoment, GameAnalysis, MoveAnalysis, PatternSummary


def make_moves() -> list[MoveAnalysis]:
    return [
        MoveAnalysis(
            move_number=1,
            side="white",
            san="e4",
            uci="e2e4",
            phase="opening",
            fen_before=chess.STARTING_FEN,
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
            maia2_played_move_prob=0.41,
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
            note="Missed the mate threat on f7.\nBraces {like this} should be stripped.",
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


def make_game(*, game_id: str = "g1", white: str = "TestPlayer", black: str = "Opponent") -> GameAnalysis:
    return GameAnalysis(
        game_id=game_id,
        event="Training game",
        site=f"https://lichess.org/{game_id}",
        date="2026.06.14",
        white=white,
        black=black,
        result="1-0",
        player_colour="white",
        headers={
            "Event": "Training game",
            "Site": f"https://lichess.org/{game_id}",
            "Date": "2026.06.14",
            "White": white,
            "Black": black,
            "Result": "1-0",
        },
        moves=make_moves(),
        critical_moments=[
            CriticalMoment(
                game_id=game_id,
                move_number=3,
                side="black",
                san="Nf6",
                phase="opening",
                fen_before="r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3",
                eval_change=3.1,
                classification="blunder",
                best_move="g7g6",
                note="Missed the mate threat on f7.",
            )
        ],
    )


def make_bundle(*games: GameAnalysis) -> AnalysisBundle:
    return AnalysisBundle(
        source_pgn="input/sample_games.pgn",
        games=list(games),
        patterns=PatternSummary(games_analysed=len(games), critical_moments=sum(len(game.critical_moments) for game in games)),
    )


def parse_games(text: str) -> list[chess.pgn.Game]:
    handle = StringIO(text)
    games: list[chess.pgn.Game] = []
    while game := chess.pgn.read_game(handle):
        games.append(game)
    return games


def node_comment(game: chess.pgn.Game, ply_index: int) -> str:
    return list(game.mainline())[ply_index].comment


def test_format_move_comment_includes_classification_eval_best_maia_and_safe_note():
    from chess_coach.annotated_pgn import format_move_comment

    move = make_moves()[5]
    comment = format_move_comment(move)

    assert comment.startswith("Chess Coach:")
    assert "blunder" in comment
    assert "eval swing +3.10" in comment
    assert "Best: g7g6" in comment
    assert "Maia2: played move 7.0%" in comment
    assert "Missed the mate threat on f7." in comment
    assert "{" not in comment
    assert "}" not in comment
    assert "\n" not in comment


def test_render_annotated_pgn_exports_parseable_game_with_headers_and_critical_comment():
    from chess_coach.annotated_pgn import render_annotated_pgn

    bundle = make_bundle(make_game())

    rendered = render_annotated_pgn(bundle)
    games = parse_games(rendered)

    assert len(games) == 1
    game = games[0]
    assert game.headers["Event"] == "Training game"
    assert game.headers["Site"] == "https://lichess.org/g1"
    assert game.headers["Date"] == "2026.06.14"
    assert game.headers["White"] == "TestPlayer"
    assert game.headers["Black"] == "Opponent"
    assert game.headers["Result"] == "1-0"
    assert node_comment(game, 5).startswith("Chess Coach:")
    assert "blunder" in node_comment(game, 5)
    assert "Best: g6" in node_comment(game, 5)
    assert "Maia2: played move 7.0%" in node_comment(game, 5)


def test_render_annotated_pgn_respects_max_games_and_annotation_scope():
    from chess_coach.annotated_pgn import render_annotated_pgn

    bundle = make_bundle(
        make_game(game_id="g1", white="TestPlayer", black="Opponent"),
        make_game(game_id="g2", white="Coach", black="Student"),
    )

    critical_only_games = parse_games(render_annotated_pgn(bundle, critical_only=True))
    assert len(critical_only_games) == 2
    assert node_comment(critical_only_games[0], 0) == ""
    assert node_comment(critical_only_games[0], 5).startswith("Chess Coach:")

    include_all_games = parse_games(render_annotated_pgn(bundle, critical_only=False, include_all_moves=True))
    assert node_comment(include_all_games[0], 0).startswith("Chess Coach:")

    limited_games = parse_games(render_annotated_pgn(bundle, max_games=1))
    assert len(limited_games) == 1
    assert limited_games[0].headers["White"] == "TestPlayer"


def test_render_annotated_pgn_honours_custom_starting_fen_headers():
    from chess_coach.annotated_pgn import render_annotated_pgn

    custom_start = "7k/8/8/8/8/8/8/K6R w - - 0 1"
    game = GameAnalysis(
        game_id="fen-game",
        event="FEN training",
        site="https://example.test/fen-game",
        date="2026.06.14",
        white="White",
        black="Black",
        result="1-0",
        headers={
            "Event": "FEN training",
            "Site": "https://example.test/fen-game",
            "Date": "2026.06.14",
            "White": "White",
            "Black": "Black",
            "Result": "1-0",
            "SetUp": "1",
            "FEN": custom_start,
        },
        moves=[
            MoveAnalysis(
                move_number=1,
                side="white",
                san="Rh8#",
                uci="h1h8",
                phase="endgame",
                fen_before=custom_start,
                eval_before=5.0,
                eval_after=99.0,
                eval_change=94.0,
                best_move="h1h8",
                classification="missed win",
            )
        ],
        critical_moments=[
            CriticalMoment(
                game_id="fen-game",
                move_number=1,
                side="white",
                san="Rh8#",
                phase="endgame",
                fen_before=custom_start,
                eval_change=94.0,
                classification="missed win",
                best_move="h1h8",
            )
        ],
    )

    rendered = render_annotated_pgn(make_bundle(game))
    parsed_game = parse_games(rendered)[0]

    assert parsed_game.headers["SetUp"] == "1"
    assert parsed_game.headers["FEN"] == custom_start
    assert node_comment(parsed_game, 0).startswith("Chess Coach:")
