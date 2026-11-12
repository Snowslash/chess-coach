"""Synthetic standard-chess setup contract across parser, engines and exports."""
from dataclasses import replace
from io import StringIO
import json

import chess
import chess.engine
import chess.pgn
from fastapi.testclient import TestClient
import pytest

from chess_coach.annotated_pgn import render_annotated_game, render_annotated_pgn
from chess_coach.config import default_config, write_env_file
from chess_coach.models import AnalysisBundle, GameAnalysis, ParsedGame, PatternSummary
from chess_coach.pgn_parser import parse_pgn_file
from chess_coach.stockfish_analyser import analyse_game, analyse_game_mock, analyse_game_stockfish
from chess_coach.web_app import create_app

SETUP_FEN = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 7 23"
SETUP_PGN = f'''[Event "Synthetic setup"]
[White "WhitePlayer"]
[Black "BlackPlayer"]
[Result "*"]
[Variant "Standard"]
[SetUp "1"]
[FEN "{SETUP_FEN}"]

23... e5 24. Nf3 Nc6 25. Bb5 a6 *
'''
NORMAL_PGN = '[Event "Synthetic ordinary"]\n[White "WhitePlayer"]\n[Black "BlackPlayer"]\n\n1. e4 e5 2. Nf3 Nc6 *\n'


def parse_text(tmp_path, text):
    path = tmp_path / "synthetic.pgn"
    path.write_text(text, encoding="utf-8")
    return parse_pgn_file(path, player="BlackPlayer")[0]


def board_trace(text):
    game = chess.pgn.read_game(StringIO(text))
    assert game is not None and not game.errors
    board = game.board()
    rows = []
    for move in game.mainline_moves():
        rows.append((board.fullmove_number, "white" if board.turn else "black", board.fen(), move.uci()))
        board.push(move)
    return rows, board.fen()


def test_parser_uses_starting_board_fullmove_number_and_side(tmp_path):
    parsed = parse_text(tmp_path, SETUP_PGN)
    assert [(m.move_number, m.side) for m in parsed.moves] == [(23, "black"), (24, "white"), (24, "black"), (25, "white"), (25, "black")]
    assert parsed.headers["SetUp"] == "1"
    assert parsed.headers["FEN"] == SETUP_FEN
    assert parsed.player_colour == "black"


@pytest.mark.parametrize("text", [SETUP_PGN, NORMAL_PGN], ids=["black-23", "ordinary"])
def test_mock_replays_the_declared_starting_board(tmp_path, text):
    parsed = parse_text(tmp_path, text)
    analysis = analyse_game_mock(parsed)
    expected, _ = board_trace(text)
    assert [(m.move_number, m.side, m.fen_before, m.uci) for m in analysis.moves] == expected
    assert analysis.headers == parsed.headers


@pytest.mark.parametrize("text", [SETUP_PGN, NORMAL_PGN], ids=["black-23", "ordinary"])
def test_stockfish_adapter_receives_declared_board_and_keeps_score_perspective(tmp_path, monkeypatch, text):
    parsed = parse_text(tmp_path, text)
    expected, final_fen = board_trace(text)
    seen_boards = []
    limits = []

    class FakeEngine:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def analyse(self, board, limit):
            seen_boards.append(board.fen())
            limits.append((limit.depth, limit.time))
            # Before +0.5, after -2.5 from the player who just moved.
            cp = 50 if len(seen_boards) % 2 else 250
            return {"score": chess.engine.PovScore(chess.engine.Cp(cp), board.turn), "pv": [next(iter(board.legal_moves))]}

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda _path: FakeEngine())
    cfg = replace(default_config(), stockfish_depth=3, stockfish_time_limit=0.01)
    result = analyse_game_stockfish(parsed, cfg, "synthetic-engine")
    assert seen_boards[::2] == [row[2] for row in expected]
    assert seen_boards[-1] == final_fen
    assert [(m.move_number, m.side, m.fen_before, m.uci) for m in result.moves] == expected
    assert all(m.eval_before == 0.5 and m.eval_after == -2.5 and m.eval_change == -3.0 for m in result.moves)
    assert limits == [(3, 0.01)] * (2 * len(expected))
    assert [(m.move_number, m.side) for m in result.critical_moments] == [(row[0], row[1]) for row in expected if row[1] == "black"]
    bundle = AnalysisBundle(source_pgn="synthetic.pgn", games=[result], patterns=PatternSummary(games_analysed=1, critical_moments=len(result.critical_moments)))
    rendered = render_annotated_pgn(bundle)
    exported = chess.pgn.read_game(StringIO(rendered))
    assert exported is not None and not exported.errors
    assert exported.end().board().fen() == final_fen
    comments = [node.comment for node in exported.mainline()]
    assert all(("blunder" in comment) == (row[1] == "black") for comment, row in zip(comments, expected, strict=True))


def test_api_setup_analysis_and_export_round_trip(tmp_path):
    root = tmp_path / "project"
    (root / "input").mkdir(parents=True)
    (root / "input/setup.pgn").write_text(SETUP_PGN)
    write_env_file(default_config(), root / ".env.stockfish")
    with TestClient(create_app(project_root=root), base_url="http://127.0.0.1") as client:
        client.headers["X-Chess-Coach-Session"] = client.get("/api/bootstrap").json()["session_token"]
        response = client.post("/api/analyse", json={"username": "BlackPlayer", "pgn_path": "input/setup.pgn", "out_path": "reports/setup.md", "mock": True})
        assert response.status_code == 200
        bundle = json.loads((root / "reports/setup.json").read_text())
        assert bundle["games"][0]["moves"][0]["fen_before"] == SETUP_FEN
        assert bundle["games"][0]["moves"][0]["move_number"] == 23
        response = client.post("/api/export-annotated-pgn", json={"json_path": "reports/setup.json", "out_path": "reports/annotated/setup.pgn", "include_all_moves": True})
        assert response.status_code == 200
    rendered = (root / "reports/annotated/setup.pgn").read_text()
    exported = chess.pgn.read_game(StringIO(rendered))
    assert exported is not None and not exported.errors
    assert exported.headers["SetUp"] == "1"
    assert exported.headers["FEN"] == SETUP_FEN
    assert exported.headers["Variant"] == "Standard"
    assert "23... e5" in rendered
    assert exported.end().board().fen() == board_trace(SETUP_PGN)[1]
    assert not (root / ".coach").exists()


@pytest.mark.parametrize("fen", [chess.STARTING_FEN, "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 23"])
def test_export_preserves_explicit_starting_headers_even_if_fen_normalizes(fen):
    analysis = GameAnalysis(game_id="setup", headers={"Variant": "Standard", "SetUp": "1", "FEN": fen})
    exported = render_annotated_game(analysis)
    assert exported.headers["SetUp"] == "1"
    assert exported.headers["FEN"] == fen
    assert exported.headers["Variant"] == "Standard"


@pytest.mark.parametrize("variant", ["Atomic", "Crazyhouse", "Chess960", "Antichess", "Unrecognised"])
def test_parser_rejects_unsupported_variants_explicitly(tmp_path, variant):
    with pytest.raises(ValueError, match="Only standard chess is supported"):
        parse_text(tmp_path, f'[Variant "{variant}"]\n\n*\n')


@pytest.mark.parametrize("boundary", ["mock", "stockfish", "fallback", "export"])
def test_analysis_and_export_do_not_treat_variant_models_as_standard(monkeypatch, boundary):
    parsed = ParsedGame(game_id="variant", headers={"Variant": "Atomic"})
    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda _path: pytest.fail("variant must be rejected before engine start"))
    with pytest.raises(ValueError, match="Only standard chess is supported"):
        if boundary == "mock":
            analyse_game_mock(parsed)
        elif boundary == "stockfish":
            analyse_game_stockfish(parsed, default_config(), "synthetic-engine")
        elif boundary == "fallback":
            analyse_game(parsed, default_config(), mock=True)
        else:
            render_annotated_game(GameAnalysis(game_id="variant", headers=parsed.headers))


@pytest.mark.parametrize("boundary", ["mock", "stockfish"])
def test_analysis_derives_number_and_side_from_board_not_stale_move_labels(tmp_path, monkeypatch, boundary):
    parsed = parse_text(tmp_path, NORMAL_PGN)
    for move in parsed.moves:
        move.move_number = 99
        move.side = "white"

    class NeutralEngine:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def analyse(self, board, _limit):
            return {"score": chess.engine.PovScore(chess.engine.Cp(0), board.turn)}

    monkeypatch.setattr(chess.engine.SimpleEngine, "popen_uci", lambda _path: NeutralEngine())
    result = (analyse_game_mock(parsed) if boundary == "mock"
              else analyse_game_stockfish(parsed, default_config(), "synthetic-engine"))
    assert [(m.move_number, m.side, m.phase) for m in result.moves] == [(1, "white", "opening"), (1, "black", "opening"), (2, "white", "opening"), (2, "black", "opening")]


def test_fen_only_chess960_castling_is_not_silently_standard(tmp_path):
    fen = chess.Board.from_chess960_pos(0).fen(shredder=True)
    with pytest.raises(ValueError, match="Only standard chess is supported"):
        parse_text(tmp_path, f'[SetUp "1"]\n[FEN "{fen}"]\n\n*\n')


@pytest.mark.parametrize("action", ["analyse", "export-annotated-pgn"])
def test_api_returns_actionable_variant_error_without_outputs(tmp_path, action):
    root = tmp_path / "project"
    root.mkdir()
    (root / "variant.pgn").write_text('[Variant "Atomic"]\n\n*\n')
    bundle = AnalysisBundle(source_pgn="variant.pgn", games=[GameAnalysis(game_id="variant", headers={"Variant": "Atomic"})], patterns=PatternSummary(games_analysed=1, critical_moments=0))
    (root / "variant.json").write_text(bundle.model_dump_json())
    payload = ({"username": "ExampleUser", "pgn_path": "variant.pgn", "out_path": "reports/rejected.md", "mock": True}
               if action == "analyse" else {"json_path": "variant.json", "out_path": "reports/rejected.pgn"})
    with TestClient(create_app(project_root=root), base_url="http://127.0.0.1", raise_server_exceptions=False) as client:
        client.headers["X-Chess-Coach-Session"] = client.get("/api/bootstrap").json()["session_token"]
        response = client.post(f"/api/{action}", json=payload)
    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert "Only standard chess is supported" in str(body["errors"])
    assert not (root / "reports").exists()
