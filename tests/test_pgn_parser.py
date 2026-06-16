from pathlib import Path

from chess_coach.pgn_parser import parse_pgn_file


def test_parse_pgn_file_extracts_headers_and_moves(tmp_path: Path):
    p = tmp_path / "games.pgn"
    p.write_text(
        """[Event "Training Game"]
[Site "Lichess"]
[Date "2026.05.30"]
[White "TestPlayer"]
[Black "Opponent"]
[Result "1-0"]
[ECO "C20"]
[Opening "King's Pawn Game"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
""",
        encoding="utf-8",
    )

    games = parse_pgn_file(p, player="TestPlayer")
    g = games[0]

    assert len(games) == 1
    assert g.event == "Training Game"
    assert g.site == "Lichess"
    assert g.date == "2026.05.30"
    assert g.white == "TestPlayer"
    assert g.black == "Opponent"
    assert g.result == "1-0"
    assert g.player_colour == "white"
    assert g.headers["ECO"] == "C20"
    assert [m.san for m in g.moves] == ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6"]
    assert [m.uci for m in g.moves][:2] == ["e2e4", "e7e5"]
    assert g.moves[0].move_number == 1
    assert g.moves[1].side == "black"


def test_parse_pgn_file_tolerates_missing_metadata(tmp_path: Path):
    p = tmp_path / "minimal.pgn"
    p.write_text("1. d4 d5 2. c4 e6 *\n", encoding="utf-8")

    games = parse_pgn_file(p)

    assert len(games) == 1
    assert games[0].event == "?"
    assert games[0].result == "*"
    assert games[0].player_colour is None
    assert len(games[0].moves) == 4
