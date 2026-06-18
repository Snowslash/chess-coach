from __future__ import annotations

import os
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

DEFAULT_ENV_FILE = ".env.stockfish"
DEFAULT_STOCKFISH_DEPTH = 12
DEFAULT_STOCKFISH_TIME_LIMIT = 0.1
DEFAULT_MAIA2_GAME_TYPE = "rapid"
DEFAULT_MAIA2_DEVICE = "cpu"
DEFAULT_MAIA2_TARGET_ELO = 1500
DEFAULT_CHESS_COACH_PGN = "input/sample_games.pgn"
DEFAULT_CHESS_COACH_OUT = "reports/latest.md"
REDACTED_SECRET = "[redacted]"


@dataclass(frozen=True)
class ChessCoachConfig:
    stockfish_path: str | None
    stockfish_depth: int
    stockfish_time_limit: float
    default_player: str | None = None
    maia2_enabled: bool = False
    maia2_game_type: str = DEFAULT_MAIA2_GAME_TYPE
    maia2_device: str = DEFAULT_MAIA2_DEVICE
    maia2_target_elo: int = DEFAULT_MAIA2_TARGET_ELO
    lichess_token: str | None = None
    default_pgn: str | None = DEFAULT_CHESS_COACH_PGN
    default_out: str | None = DEFAULT_CHESS_COACH_OUT


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        try:
            parts = shlex.split(line, comments=False, posix=True)
            assignment = parts[0] if parts else line
            parsed_with_shlex = True
        except ValueError:
            assignment = line
            parsed_with_shlex = False
        key, value = assignment.split("=", 1)
        key = key.strip()
        if not parsed_with_shlex:
            value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def parse_env_file(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    return parse_env_text(env_path.read_text(encoding="utf-8"))


# Backwards-compatible alias used by older code/tests.
def _parse_env_stockfish(path: Path) -> dict[str, str]:
    return parse_env_file(path)



def _config_value(values: Mapping[str, str], key: str, default: str | None = None) -> str | None:
    return os.getenv(key) or values.get(key) or default



def _config_bool(values: Mapping[str, str], key: str, default: bool = False) -> bool:
    raw = _config_value(values, key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}



def _mapping_value(values: Mapping[str, str], key: str, default: str | None = None, *, use_environment: bool) -> str | None:
    if use_environment:
        return _config_value(values, key, default)
    return values.get(key) or default



def _mapping_bool(values: Mapping[str, str], key: str, default: bool = False, *, use_environment: bool) -> bool:
    raw = _mapping_value(values, key, use_environment=use_environment)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}



def config_from_env_values(values: Mapping[str, str], *, use_environment: bool = True) -> ChessCoachConfig:
    return ChessCoachConfig(
        stockfish_path=_mapping_value(values, "STOCKFISH_PATH", use_environment=use_environment) or None,
        stockfish_depth=int(
            _mapping_value(values, "STOCKFISH_DEPTH", str(DEFAULT_STOCKFISH_DEPTH), use_environment=use_environment)
            or str(DEFAULT_STOCKFISH_DEPTH)
        ),
        stockfish_time_limit=float(
            _mapping_value(values, "STOCKFISH_TIME_LIMIT", str(DEFAULT_STOCKFISH_TIME_LIMIT), use_environment=use_environment)
            or str(DEFAULT_STOCKFISH_TIME_LIMIT)
        ),
        default_player=_mapping_value(values, "CHESS_COACH_PLAYER", use_environment=use_environment) or None,
        maia2_enabled=_mapping_bool(values, "MAIA2_ENABLED", False, use_environment=use_environment),
        maia2_game_type=_mapping_value(values, "MAIA2_GAME_TYPE", DEFAULT_MAIA2_GAME_TYPE, use_environment=use_environment)
        or DEFAULT_MAIA2_GAME_TYPE,
        maia2_device=_mapping_value(values, "MAIA2_DEVICE", DEFAULT_MAIA2_DEVICE, use_environment=use_environment) or DEFAULT_MAIA2_DEVICE,
        maia2_target_elo=int(
            _mapping_value(values, "MAIA2_TARGET_ELO", str(DEFAULT_MAIA2_TARGET_ELO), use_environment=use_environment)
            or str(DEFAULT_MAIA2_TARGET_ELO)
        ),
        lichess_token=_mapping_value(values, "LICHESS_TOKEN", use_environment=use_environment) or None,
        default_pgn=_mapping_value(values, "CHESS_COACH_PGN", DEFAULT_CHESS_COACH_PGN, use_environment=use_environment)
        or DEFAULT_CHESS_COACH_PGN,
        default_out=_mapping_value(values, "CHESS_COACH_OUT", DEFAULT_CHESS_COACH_OUT, use_environment=use_environment)
        or DEFAULT_CHESS_COACH_OUT,
    )



def config_to_env_values(config: ChessCoachConfig, *, redact_token: bool = False) -> dict[str, str]:
    token_value = config.lichess_token or ""
    if redact_token and token_value:
        token_value = REDACTED_SECRET
    return {
        "STOCKFISH_PATH": config.stockfish_path or "",
        "STOCKFISH_DEPTH": str(config.stockfish_depth),
        "STOCKFISH_TIME_LIMIT": str(config.stockfish_time_limit),
        "CHESS_COACH_PLAYER": config.default_player or "",
        "LICHESS_TOKEN": token_value,
        "CHESS_COACH_PGN": config.default_pgn or DEFAULT_CHESS_COACH_PGN,
        "CHESS_COACH_OUT": config.default_out or DEFAULT_CHESS_COACH_OUT,
        "MAIA2_ENABLED": "true" if config.maia2_enabled else "false",
        "MAIA2_GAME_TYPE": config.maia2_game_type,
        "MAIA2_DEVICE": config.maia2_device,
        "MAIA2_TARGET_ELO": str(config.maia2_target_elo),
    }



def _export_line(key: str, value: str | int | float | bool) -> str:
    return f"export {key}={shlex.quote(str(value))}"


def render_env_file(config: ChessCoachConfig, *, redact_token: bool = False) -> str:
    values = config_to_env_values(config, redact_token=redact_token)
    lines = [
        "# Chess Coach local runtime configuration.",
        "# This file is shared by the CLI and the desktop GUI.",
        "# Do not commit machine-specific paths or real secrets.",
        "",
        "# Path to a locally installed Stockfish binary.",
        _export_line("STOCKFISH_PATH", values["STOCKFISH_PATH"]),
        _export_line("STOCKFISH_DEPTH", values["STOCKFISH_DEPTH"]),
        _export_line("STOCKFISH_TIME_LIMIT", values["STOCKFISH_TIME_LIMIT"]),
        "",
        "# Lichess username and optional token.",
        _export_line("CHESS_COACH_PLAYER", values["CHESS_COACH_PLAYER"]),
        _export_line("LICHESS_TOKEN", values["LICHESS_TOKEN"]),
        "",
        "# Default local input/output paths.",
        _export_line("CHESS_COACH_PGN", values["CHESS_COACH_PGN"]),
        _export_line("CHESS_COACH_OUT", values["CHESS_COACH_OUT"]),
        "",
        "# Optional Maia 2 human-likeness analysis.",
        _export_line("MAIA2_ENABLED", values["MAIA2_ENABLED"]),
        _export_line("MAIA2_GAME_TYPE", values["MAIA2_GAME_TYPE"]),
        _export_line("MAIA2_DEVICE", values["MAIA2_DEVICE"]),
        _export_line("MAIA2_TARGET_ELO", values["MAIA2_TARGET_ELO"]),
        "",
    ]
    return "\n".join(lines)



def write_env_file(config: ChessCoachConfig, path: str | Path, *, redact_token: bool = False) -> Path:
    env_path = Path(path)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(render_env_file(config, redact_token=redact_token), encoding="utf-8")
    return env_path



def default_config() -> ChessCoachConfig:
    return ChessCoachConfig(
        stockfish_path=None,
        stockfish_depth=DEFAULT_STOCKFISH_DEPTH,
        stockfish_time_limit=DEFAULT_STOCKFISH_TIME_LIMIT,
        default_player=None,
        maia2_enabled=False,
        maia2_game_type=DEFAULT_MAIA2_GAME_TYPE,
        maia2_device=DEFAULT_MAIA2_DEVICE,
        maia2_target_elo=DEFAULT_MAIA2_TARGET_ELO,
        lichess_token=None,
        default_pgn=DEFAULT_CHESS_COACH_PGN,
        default_out=DEFAULT_CHESS_COACH_OUT,
    )



def config_as_dict(config: ChessCoachConfig, *, redact_token: bool = False) -> dict[str, str | int | float | bool | None]:
    data = asdict(config)
    if redact_token and data.get("lichess_token"):
        data["lichess_token"] = REDACTED_SECRET
    return data



def load_config(env_file: str | Path = DEFAULT_ENV_FILE) -> ChessCoachConfig:
    return config_from_env_values(parse_env_file(env_file))
