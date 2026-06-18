from __future__ import annotations

import json
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse

import pytest

from chess_coach.config import (
    ChessCoachConfig,
    load_config,
    parse_env_file,
    render_env_file,
    write_env_file,
)
from chess_coach.gui_support import (
    create_diagnostic_bundle,
    probe_lichess_user,
    redact_secret,
    redact_text,
    validate_gui_config,
)


class FakeResponse:
    def __init__(self, body: str):
        self.body = body.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body



def make_config(**overrides) -> ChessCoachConfig:
    values = dict(
        stockfish_path="/opt/stockfish/stockfish",
        stockfish_depth=14,
        stockfish_time_limit=0.25,
        default_player="ExampleUser",
        maia2_enabled=True,
        maia2_game_type="rapid",
        maia2_device="cpu",
        maia2_target_elo=1500,
        lichess_token="top-secret-token",
        default_pgn="input/example.pgn",
        default_out="reports/example.md",
    )
    values.update(overrides)
    return ChessCoachConfig(**values)



def test_env_file_roundtrip_reads_all_gui_relevant_values(tmp_path: Path):
    env_file = tmp_path / ".env.stockfish"
    config = make_config()

    write_env_file(config, env_file)

    parsed = parse_env_file(env_file)
    assert parsed["STOCKFISH_PATH"] == "/opt/stockfish/stockfish"
    assert parsed["STOCKFISH_DEPTH"] == "14"
    assert parsed["STOCKFISH_TIME_LIMIT"] == "0.25"
    assert parsed["CHESS_COACH_PLAYER"] == "ExampleUser"
    assert parsed["LICHESS_TOKEN"] == "top-secret-token"
    assert parsed["CHESS_COACH_PGN"] == "input/example.pgn"
    assert parsed["CHESS_COACH_OUT"] == "reports/example.md"
    assert parsed["MAIA2_ENABLED"] == "true"
    assert parsed["MAIA2_GAME_TYPE"] == "rapid"
    assert parsed["MAIA2_DEVICE"] == "cpu"
    assert parsed["MAIA2_TARGET_ELO"] == "1500"

    loaded = load_config(env_file)
    assert loaded == config



def test_render_env_file_can_redact_token_without_changing_other_values():
    rendered = render_env_file(make_config(), redact_token=True)

    assert "export LICHESS_TOKEN='[redacted]'" in rendered
    assert "export CHESS_COACH_PLAYER=ExampleUser" in rendered
    assert "STOCKFISH_DEPTH=14" in rendered
    assert "top-secret-token" not in rendered



def test_render_env_file_shell_quotes_values_safely_when_sourced(tmp_path: Path):
    marker = tmp_path / "pwned"
    malicious = f'"; touch {marker}; #'
    env_file = tmp_path / ".env.stockfish"
    write_env_file(make_config(stockfish_path=malicious, default_player="ExampleUser"), env_file)

    result = subprocess.run(
        ["bash", "-c", f"set -euo pipefail; source {env_file}; test \"$STOCKFISH_PATH\" = {malicious!r}"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert load_config(env_file).stockfish_path == malicious


def test_validate_gui_config_rejects_line_breaks_before_writing_shell_env():
    result = validate_gui_config({"stockfish_path": "safe\nBAD=1", "stockfish_depth": 12, "stockfish_time_limit": 0.1, "maia2_game_type": "rapid", "maia2_target_elo": 1500})

    assert result["ok"] is False
    assert result["errors"]["stockfish_path"] == "Remove line breaks or control characters."


def test_validate_gui_config_accepts_expected_values():
    result = validate_gui_config(
        {
            "default_player": "ExampleUser",
            "lichess_token": "top-secret-token",
            "default_pgn": "input/example.pgn",
            "default_out": "reports/example.md",
            "stockfish_path": "C:/Stockfish/stockfish.exe",
            "stockfish_depth": 12,
            "stockfish_time_limit": 0.5,
            "maia2_enabled": True,
            "maia2_game_type": "rapid",
            "maia2_device": "cuda",
            "maia2_target_elo": 1500,
        },
        require_username=True,
    )

    assert result["ok"] is True
    assert result["errors"] == {}
    assert result["warnings"] == {}



def test_validate_gui_config_rejects_invalid_values_and_warns_on_absolute_paths():
    result = validate_gui_config(
        {
            "default_player": "bad name!",
            "default_pgn": "/tmp/example.pgn",
            "default_out": "/tmp/example.md",
            "stockfish_depth": 0,
            "stockfish_time_limit": 40,
            "maia2_enabled": True,
            "maia2_game_type": "ultrabullet",
            "maia2_device": "gpu",
            "maia2_target_elo": 999,
        },
        require_username=True,
    )

    assert result["ok"] is False
    assert "default_player" in result["errors"]
    assert "stockfish_depth" in result["errors"]
    assert "stockfish_time_limit" in result["errors"]
    assert "maia2_game_type" in result["errors"]
    assert "maia2_target_elo" in result["errors"]
    assert "default_pgn" in result["warnings"]
    assert "default_out" in result["warnings"]
    assert "maia2_device" in result["warnings"]



def test_redaction_helpers_remove_secret_values_from_text():
    assert redact_secret("top-secret-token") == "[redacted]"
    assert redact_text("token=top-secret-token", ["top-secret-token"]) == "token=[redacted]"



def test_probe_lichess_user_uses_lichess_org_and_only_adds_token_header_when_requested():
    seen = []

    def fake_urlopen(request, timeout):
        seen.append((request.full_url, dict(request.header_items()), timeout))
        return FakeResponse('{"id": "exampleuser", "username": "ExampleUser"}')

    result = probe_lichess_user("ExampleUser", token="secret-token", urlopen=fake_urlopen)

    assert result["ok"] is True
    url, headers, timeout = seen[0]
    assert urlparse(url).scheme == "https"
    assert urlparse(url).netloc == "lichess.org"
    assert headers["Authorization"] == "Bearer secret-token"
    assert timeout == 15



def test_probe_lichess_user_reports_missing_user_without_leaking_token():
    token = "secret-token"

    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 404, "Not found", hdrs=None, fp=None)

    result = probe_lichess_user("MissingUser", token=token, urlopen=fake_urlopen)

    assert result["ok"] is False
    assert result["status"] == "missing"
    assert token not in json.dumps(result)



def test_create_diagnostic_bundle_redacts_token_and_excludes_artifacts_by_default(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    env_file = project / ".env.stockfish"
    config = make_config(default_pgn="input/private_games.pgn", default_out="reports/private.md")
    write_env_file(config, env_file)

    pgn_path = project / "input" / "private_games.pgn"
    pgn_path.parent.mkdir(parents=True)
    pgn_path.write_text('[Event "Private"]\n\n1. e4 *\n', encoding="utf-8")

    report_path = project / "reports" / "private.md"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("secret report contents", encoding="utf-8")
    (project / "reports" / "private.json").write_text('{"token": "top-secret-token"}', encoding="utf-8")

    bundle_dir = create_diagnostic_bundle(
        project_root=project,
        env_file=env_file,
        readiness={"stockfish": {"status": "missing"}},
        recent_logs=["using token top-secret-token"],
        electron_context={"platform": "win32"},
        include_pgn=False,
        include_report=False,
    )

    metadata = json.loads((bundle_dir / "metadata.json").read_text(encoding="utf-8"))
    redacted_env = (bundle_dir / "redacted_config.env").read_text(encoding="utf-8")
    logs = (bundle_dir / "recent_logs.txt").read_text(encoding="utf-8")

    assert metadata["config"]["lichess_token"] == "[redacted]"
    assert "top-secret-token" not in json.dumps(metadata)
    assert "top-secret-token" not in redacted_env
    assert "export LICHESS_TOKEN='[redacted]'" in redacted_env
    assert "top-secret-token" not in logs
    assert "[redacted]" in logs
    assert not (bundle_dir / "private_games.pgn").exists()
    assert not (bundle_dir / "private.md").exists()
    assert not (bundle_dir / "private.json").exists()
