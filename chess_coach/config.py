from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ChessCoachConfig:
    stockfish_path: str | None
    stockfish_depth: int
    stockfish_time_limit: float
    default_player: str | None = None
    maia2_enabled: bool = False
    maia2_game_type: str = "rapid"
    maia2_device: str = "cpu"
    maia2_target_elo: int = 1500


def _parse_env_stockfish(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _config_value(values: dict[str, str], key: str, default: str | None = None) -> str | None:
    return os.getenv(key) or values.get(key) or default


def _config_bool(values: dict[str, str], key: str, default: bool = False) -> bool:
    raw = _config_value(values, key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_config(env_file: str | Path = ".env.stockfish") -> ChessCoachConfig:
    file_values = _parse_env_stockfish(Path(env_file))
    return ChessCoachConfig(
        _config_value(file_values, "STOCKFISH_PATH") or None,
        int(_config_value(file_values, "STOCKFISH_DEPTH", "12") or "12"),
        float(_config_value(file_values, "STOCKFISH_TIME_LIMIT", "0.1") or "0.1"),
        _config_value(file_values, "CHESS_COACH_PLAYER") or None,
        _config_bool(file_values, "MAIA2_ENABLED", False),
        _config_value(file_values, "MAIA2_GAME_TYPE", "rapid") or "rapid",
        _config_value(file_values, "MAIA2_DEVICE", "cpu") or "cpu",
        int(_config_value(file_values, "MAIA2_TARGET_ELO", "1500") or "1500"),
    )
