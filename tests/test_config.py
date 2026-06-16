import os
from pathlib import Path

from chess_coach.config import load_config


def test_load_config_reads_project_env_stockfish_file(tmp_path: Path, monkeypatch):
    env_file = tmp_path / ".env.stockfish"
    env_file.write_text(
        'export STOCKFISH_PATH="/custom/bin/stockfish"\n'
        "STOCKFISH_DEPTH=15\n"
        "STOCKFISH_TIME_LIMIT=0.25\n"
        "CHESS_COACH_PLAYER=exampleuser\n"
        "MAIA2_ENABLED=true\n"
        "MAIA2_GAME_TYPE=blitz\n"
        "MAIA2_DEVICE=gpu\n"
        "MAIA2_TARGET_ELO=1750\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    for key in [
        "STOCKFISH_PATH",
        "STOCKFISH_DEPTH",
        "STOCKFISH_TIME_LIMIT",
        "CHESS_COACH_PLAYER",
        "MAIA2_ENABLED",
        "MAIA2_GAME_TYPE",
        "MAIA2_DEVICE",
        "MAIA2_TARGET_ELO",
    ]:
        monkeypatch.delenv(key, raising=False)

    config = load_config()

    assert config.stockfish_path == "/custom/bin/stockfish"
    assert config.stockfish_depth == 15
    assert config.stockfish_time_limit == 0.25
    assert config.default_player == "exampleuser"
    assert config.maia2_enabled is True
    assert config.maia2_game_type == "blitz"
    assert config.maia2_device == "gpu"
    assert config.maia2_target_elo == 1750


def test_load_config_environment_overrides_env_stockfish_file(tmp_path: Path, monkeypatch):
    (tmp_path / ".env.stockfish").write_text("STOCKFISH_DEPTH=10\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("STOCKFISH_DEPTH", "18")

    assert load_config().stockfish_depth == 18
