from __future__ import annotations

import json
from pathlib import Path

import pytest

from chess_coach.config import DEFAULT_CHESS_COACH_OUT, DEFAULT_CHESS_COACH_PGN, REDACTED_SECRET
from chess_coach.gui_support import render_env_file
from chess_coach.web_app import create_app


def make_client(tmp_path: Path, **overrides):
    from fastapi.testclient import TestClient

    project_root = tmp_path / "project"
    project_root.mkdir(exist_ok=True)
    env_file = project_root / ".env.stockfish"
    kwargs = {
        "project_root": project_root,
        "env_file": env_file,
    }
    kwargs.update(overrides)
    app = create_app(**kwargs)
    return TestClient(app), project_root, env_file


def test_bootstrap_reports_local_loopback_privacy_defaults(tmp_path: Path):
    client, project_root, env_file = make_client(tmp_path)

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["app"]["name"] == "Chess Coach"
    assert payload["paths"]["project_root"] == str(project_root)
    assert payload["paths"]["config_path"] == str(env_file)
    assert payload["paths"]["default_pgn"] == DEFAULT_CHESS_COACH_PGN
    assert payload["paths"]["default_out"] == DEFAULT_CHESS_COACH_OUT
    assert payload["privacy"]["bind_host"] == "127.0.0.1"
    assert payload["privacy"]["local_only"] is True
    assert payload["privacy"]["telemetry"] is False
    assert "lichess.org" in payload["privacy"]["token_boundary"]


def test_config_endpoint_returns_defaults_when_env_file_missing(tmp_path: Path):
    client, _, env_file = make_client(tmp_path)

    response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["exists"] is False
    assert payload["env_file"] == str(env_file)
    assert payload["config"]["default_pgn"] == DEFAULT_CHESS_COACH_PGN
    assert payload["config"]["default_out"] == DEFAULT_CHESS_COACH_OUT
    assert payload["config"]["lichess_token"] == ""
    assert payload["validation"]["ok"] is True


def test_validate_config_rejects_invalid_values(tmp_path: Path):
    client, _, _ = make_client(tmp_path)

    response = client.post(
        "/api/config/validate",
        json={
            "default_player": "bad name!",
            "stockfish_depth": 0,
            "stockfish_time_limit": 50,
            "maia2_game_type": "hyperbullet",
            "maia2_target_elo": 999,
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["ok"] is False
    assert set(payload["errors"]).issuperset(
        {"default_player", "stockfish_depth", "stockfish_time_limit", "maia2_game_type", "maia2_target_elo"}
    )


def test_save_config_writes_env_file_and_redacts_token_in_response(tmp_path: Path):
    client, _, env_file = make_client(tmp_path)

    response = client.post(
        "/api/config",
        json={
            "default_player": "ExampleUser",
            "lichess_token": "secret-token",
            "default_pgn": "input/example.pgn",
            "default_out": "reports/example.md",
            "stockfish_path": "C:/Stockfish/stockfish.exe",
            "stockfish_depth": 12,
            "stockfish_time_limit": 0.5,
            "maia2_enabled": False,
            "maia2_game_type": "rapid",
            "maia2_device": "cpu",
            "maia2_target_elo": 1500,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["path"] == str(env_file)
    assert payload["config"]["lichess_token"] == REDACTED_SECRET
    assert env_file.exists()
    written = env_file.read_text(encoding="utf-8")
    assert "secret-token" in written
    assert "export CHESS_COACH_PLAYER=ExampleUser" in written


def test_readiness_endpoint_uses_injected_collector(tmp_path: Path):
    expected = {
        "stockfish": {"status": "available", "details": "Stockfish 16"},
        "maia": {"status": "disabled", "details": "Not enabled"},
    }
    client, _, _ = make_client(tmp_path, readiness_collector=lambda config: expected)

    response = client.get("/api/readiness")

    assert response.status_code == 200
    assert response.json() == expected


def test_lichess_probe_endpoint_does_not_echo_token(tmp_path: Path):
    seen = {}

    def fake_probe(username: str, token: str | None):
        seen["username"] = username
        seen["token"] = token
        return {
            "ok": True,
            "status": "available",
            "message": f"Found {username}",
            "username": username,
            "token_used": bool(token),
        }

    client, _, _ = make_client(tmp_path, lichess_probe=fake_probe)

    response = client.post("/api/lichess/test", json={"username": "ExampleUser", "token": "secret-token"})

    assert response.status_code == 200
    payload = response.json()
    assert seen == {"username": "ExampleUser", "token": "secret-token"}
    assert payload["ok"] is True
    assert json.dumps(payload).find("secret-token") == -1
    assert payload["token_used"] is True


def test_import_lichess_endpoint_validates_then_executes_runner(tmp_path: Path):
    calls = []

    def fake_runner(payload):
        calls.append(payload)
        return {"ok": True, "out_path": "input/lichess_recent_example.pgn", "stdout": "Imported"}

    client, _, _ = make_client(tmp_path, workflow_runners={"import_lichess": fake_runner})

    response = client.post(
        "/api/import-lichess",
        json={
            "username": "ExampleUser",
            "max_games": 12,
            "perf": "rapid",
            "rated_only": True,
            "since_days": 7,
            "out_path": "input/lichess_recent_example.pgn",
        },
    )

    assert response.status_code == 200
    assert calls == [
        {
            "username": "ExampleUser",
            "max_games": 12,
            "perf": "rapid",
            "rated_only": True,
            "since_days": 7,
            "out_path": "input/lichess_recent_example.pgn",
        }
    ]
    assert response.json()["out_path"] == "input/lichess_recent_example.pgn"


@pytest.mark.parametrize(
    ("path", "payload", "expected_error"),
    [
        (
            "/api/import-lichess",
            {"username": "", "max_games": 20, "out_path": "input/recent.pgn"},
            "username",
        ),
        (
            "/api/analyse",
            {"username": "ExampleUser", "pgn_path": "", "out_path": "reports/latest.md"},
            "pgn_path",
        ),
        (
            "/api/export-annotated-pgn",
            {"json_path": "", "out_path": "reports/annotated/latest.pgn"},
            "json_path",
        ),
    ],
)
def test_workflow_endpoints_reject_invalid_input_before_execution(tmp_path: Path, path: str, payload: dict[str, object], expected_error: str):
    called = False

    def fake_runner(_payload):
        nonlocal called
        called = True
        return {"ok": True}

    client, _, _ = make_client(
        tmp_path,
        workflow_runners={
            "import_lichess": fake_runner,
            "analyse": fake_runner,
            "export_annotated_pgn": fake_runner,
        },
    )

    response = client.post(path, json=payload)

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert expected_error in body["errors"]
    assert called is False


def test_analyse_endpoint_returns_paths_from_runner(tmp_path: Path):
    project_root = tmp_path / "project"
    (project_root / "input").mkdir(parents=True)
    (project_root / "input" / "recent.pgn").write_text('[Event "Game"]\n\n1. e4 *\n', encoding="utf-8")
    client, _, _ = make_client(
        tmp_path,
        workflow_runners={
            "analyse": lambda payload: {
                "ok": True,
                "markdown_path": payload["out_path"],
                "json_path": "reports/latest.json",
                "stdout": "Analysis complete",
                "stderr": "",
            }
        },
    )

    response = client.post(
        "/api/analyse",
        json={"username": "ExampleUser", "pgn_path": "input/recent.pgn", "out_path": "reports/latest.md"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["markdown_path"] == "reports/latest.md"
    assert payload["json_path"] == "reports/latest.json"


def test_export_annotated_pgn_endpoint_passes_flags_to_runner(tmp_path: Path):
    project_root = tmp_path / "project"
    (project_root / "reports").mkdir(parents=True)
    (project_root / "reports" / "latest.json").write_text("{}", encoding="utf-8")
    calls = []
    client, _, _ = make_client(
        tmp_path,
        workflow_runners={
            "export_annotated_pgn": lambda payload: calls.append(payload) or {
                "ok": True,
                "out_path": payload["out_path"],
                "stdout": "Exported",
                "stderr": "",
            }
        },
    )

    response = client.post(
        "/api/export-annotated-pgn",
        json={
            "json_path": "reports/latest.json",
            "out_path": "reports/annotated/latest.pgn",
            "max_games": 5,
            "critical_only": True,
            "include_all_moves": False,
        },
    )

    assert response.status_code == 200
    assert calls == [
        {
            "json_path": "reports/latest.json",
            "out_path": "reports/annotated/latest.pgn",
            "max_games": 5,
            "critical_only": True,
            "include_all_moves": False,
        }
    ]
    assert response.json()["out_path"] == "reports/annotated/latest.pgn"


def test_diagnostics_endpoint_creates_bundle_with_explicit_inclusion_flags(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir(exist_ok=True)
    env_file = project_root / ".env.stockfish"
    env_file.write_text(render_env_file(create_app(project_root=project_root, env_file=env_file).state.default_config), encoding="utf-8")

    captured = {}

    def fake_bundle_creator(**kwargs):
        captured.update(kwargs)
        bundle_dir = project_root / ".coach" / "diagnostics" / "bundle-1"
        bundle_dir.mkdir(parents=True)
        (bundle_dir / "metadata.json").write_text("{}", encoding="utf-8")
        return bundle_dir

    client, _, _ = make_client(tmp_path, diagnostic_bundle_creator=fake_bundle_creator)

    response = client.post(
        "/api/diagnostics",
        json={
            "include_pgn": True,
            "include_report": False,
            "selected_paths": {"pgn": "input/recent.pgn", "report": "reports/latest.md"},
            "recent_logs": ["token=[redacted]"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["path"].endswith("bundle-1")
    assert captured["include_pgn"] is True
    assert captured["include_report"] is False
    assert captured["selected_paths"] == {"pgn": "input/recent.pgn", "report": "reports/latest.md"}
