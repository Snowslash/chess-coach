from chess_coach.config import ChessCoachConfig
from chess_coach.maia2_analyser import annotate_games_with_maia2, maia2_available
from chess_coach.models import GameAnalysis, MoveAnalysis


def _config(**overrides):
    values = dict(
        stockfish_path=None,
        stockfish_depth=12,
        stockfish_time_limit=0.1,
        maia2_enabled=False,
        maia2_game_type="rapid",
        maia2_device="cpu",
        maia2_target_elo=1500,
    )
    values.update(overrides)
    return ChessCoachConfig(**values)


def test_maia2_availability_is_disabled_by_default():
    status = maia2_available(_config())

    assert status.enabled is False
    assert status.available is False
    assert status.reason == "disabled"


def test_maia2_availability_reports_missing_optional_package(monkeypatch):
    monkeypatch.setattr("chess_coach.maia2_analyser.importlib.util.find_spec", lambda name: None)

    status = maia2_available(_config(maia2_enabled=True))

    assert status.enabled is True
    assert status.available is False
    assert "maia2" in (status.reason or "")


def test_maia2_availability_reports_missing_transitive_dependency(monkeypatch):
    def fake_find_spec(name):
        if name == "gdown":
            return None
        return object()

    monkeypatch.setattr("chess_coach.maia2_analyser.importlib.util.find_spec", fake_find_spec)

    status = maia2_available(_config(maia2_enabled=True))

    assert status.enabled is True
    assert status.available is False
    assert "gdown" in (status.reason or "")
    assert "pip install" in (status.reason or "")


def test_annotate_games_with_maia2_adds_played_probability_and_top_moves():
    game = GameAnalysis(
        game_id="g1",
        player_colour="white",
        moves=[
            MoveAnalysis(
                move_number=12,
                side="white",
                san="Nxe5?",
                uci="f3e5",
                phase="middlegame",
                fen_before="r1bqkbnr/pppp1ppp/2n5/4N3/4P3/8/PPPP1PPP/RNBQKB1R w KQkq - 0 4",
            ),
            MoveAnalysis(
                move_number=12,
                side="black",
                san="Nxe5",
                uci="c6e5",
                phase="middlegame",
                fen_before="r1bqkbnr/pppp1ppp/2n5/4N3/4P3/8/PPPP1PPP/RNBQKB1R b KQkq - 0 4",
            ),
        ],
    )

    def fake_inference_each(model, prepared, fen, elo_self, elo_oppo):
        assert model == "model"
        assert prepared == "prepared"
        assert elo_self == 1500
        assert elo_oppo == 1500
        return {"d2d4": 0.31, "f3e5": 0.08, "g1f3": 0.07}, 0.42

    annotate_games_with_maia2([game], "model", "prepared", 1500, fake_inference_each, top_n=2)

    white_move = game.moves[0]
    black_move = game.moves[1]
    assert white_move.maia2_played_move_prob == 0.08
    assert white_move.maia2_top_moves == {"d2d4": 0.31, "f3e5": 0.08}
    assert white_move.maia2_win_prob == 0.42
    assert black_move.maia2_played_move_prob is None
