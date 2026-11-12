"""Operation runtime regressions with synthetic PGNs and fake optional Maia only."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from threading import Event
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from chess_coach import cli, pipeline, web_app
from chess_coach.config import default_config, write_env_file
from chess_coach.maia2_analyser import Maia2Status
from chess_coach.stockfish_analyser import analyse_game_mock


@pytest.fixture(autouse=True)
def isolated_config_environment(monkeypatch):
    for key in tuple(os.environ):
        if key.startswith(("STOCKFISH_", "MAIA2_", "CHESS_COACH_", "LICHESS_")):
            monkeypatch.delenv(key)


def make_project(root):
    (root / "input").mkdir(parents=True)
    (root / "input/game.pgn").write_text(
        '[Event "Synthetic runtime regression"]\n[White "ExampleUser"]\n\n1. e4 e5 *\n'
    )


def client_for(root, env_file=None):
    client = TestClient(web_app.create_app(project_root=root, env_file=env_file), base_url="http://127.0.0.1")
    client.headers["X-Chess-Coach-Session"] = client.get("/api/bootstrap").json()["session_token"]
    return client


def analyse(client):
    return client.post("/api/analyse", json={
        "username": "ExampleUser", "pgn_path": "input/game.pgn",
        "out_path": "reports/result.md", "mock": True,
    })


def fake_optional_maia(monkeypatch, from_pretrained):
    # Keep the real pipeline and runtime loader. Replace only package/model APIs;
    # the default save_root below matches the lockfile-pinned Maia 0.9 API.
    monkeypatch.setattr(pipeline, "maia2_available", lambda config: Maia2Status(
        enabled=config.maia2_enabled, available=config.maia2_enabled,
    ))
    monkeypatch.setitem(sys.modules, "maia2.model", SimpleNamespace(from_pretrained=from_pretrained))
    monkeypatch.setitem(sys.modules, "maia2.inference", SimpleNamespace(
        prepare=lambda: "synthetic-prepared",
        inference_each=lambda model, *_args: ({"e2e4": model}, 0.5),
    ))


def test_overlapping_maia_operations_use_their_project_caches_without_chdir(tmp_path, monkeypatch):
    roots = {name: tmp_path / name for name in ("rapid", "blitz")}
    entered = {name: Event() for name in roots}
    release = {name: Event() for name in roots}
    seen = {}
    clients = {}
    for index, (name, root) in enumerate(roots.items()):
        make_project(root)
        selected = tmp_path / "settings" / f"{name}.env"
        write_env_file(replace(default_config(), maia2_enabled=True, maia2_game_type=name), selected)
        marker = root / "maia2_models/synthetic-probability.txt"
        marker.parent.mkdir()
        marker.write_text(str(0.2 + index * 0.5))
        clients[name] = client_for(root, selected)

    launch = tmp_path / "launch"
    launch.mkdir()
    monkeypatch.chdir(launch)
    cwd_changes = []
    monkeypatch.setattr(os, "chdir", lambda path: cwd_changes.append(path))

    def from_pretrained(type, device, save_root="./maia2_models"):
        cache = Path(save_root)
        seen[type] = (cache, Path.cwd(), device)
        entered[type].set()
        assert release[type].wait(5), "test did not release model boundary"
        marker = cache / "synthetic-probability.txt"
        return float(marker.read_text()) if marker.is_file() else 0.0

    fake_optional_maia(monkeypatch, from_pretrained)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(analyse, clients["rapid"])
            try:
                assert entered["rapid"].wait(5)
                second = pool.submit(analyse, clients["blitz"])
                assert entered["blitz"].wait(5)
                release["rapid"].set()
                first_response = first.result(timeout=5)
                release["blitz"].set()
                second_response = second.result(timeout=5)
            finally:
                for event in release.values():
                    event.set()
    finally:
        for client in clients.values():
            client.close()

    assert first_response.status_code == second_response.status_code == 200
    assert cwd_changes == []
    assert Path.cwd() == launch
    for index, (name, root) in enumerate(roots.items()):
        cache, observed_cwd, device = seen[name]
        assert cache == root / "maia2_models", "Maia must receive the absolute operation cache, not its cwd default"
        assert cache.is_absolute()
        assert observed_cwd == launch
        assert device == "cpu"
        bundle = json.loads((root / "reports/result.json").read_text())
        assert bundle["metadata"]["maia2_available"] is True
        assert bundle["metadata"]["maia2_game_type"] == name
        assert bundle["games"][0]["moves"][0]["maia2_played_move_prob"] == 0.2 + index * 0.5
    assert not (launch / "maia2_models").exists()
    assert not (tmp_path / "settings/maia2_models").exists()


def test_cli_without_operation_context_retains_launch_directory_maia_cache(tmp_path, monkeypatch):
    root = tmp_path / "data"
    make_project(root)
    launch = tmp_path / "launch"
    launch.mkdir()
    write_env_file(replace(default_config(), maia2_enabled=True), launch / ".env.stockfish")
    marker = launch / "maia2_models/synthetic-probability.txt"
    marker.parent.mkdir()
    marker.write_text("0.6")
    caches = []

    def from_pretrained(type, device, save_root="./maia2_models"):
        caches.append(Path(save_root).resolve())
        return float((Path(save_root) / marker.name).read_text())

    fake_optional_maia(monkeypatch, from_pretrained)
    monkeypatch.chdir(launch)
    result = cli.main(["analyse", "--pgn", str(root / "input/game.pgn"),
                       "--out", str(root / "reports/result.md"), "--player", "ExampleUser", "--mock"])
    assert result == 0
    assert caches == [launch / "maia2_models"]
    bundle = json.loads((root / "reports/result.json").read_text())
    assert bundle["metadata"]["maia2_available"] is True
    assert bundle["games"][0]["moves"][0]["maia2_played_move_prob"] == 0.6
    assert not (root / "maia2_models").exists()
    assert Path.cwd() == launch


def test_project_maia_load_failure_remains_optional_and_visible(tmp_path, monkeypatch):
    root = tmp_path / "project"
    make_project(root)
    write_env_file(replace(default_config(), maia2_enabled=True), root / ".env.stockfish")
    caches = []

    def from_pretrained(type, device, save_root="./maia2_models"):
        caches.append(Path(save_root))
        raise OSError("synthetic model cache unavailable")

    fake_optional_maia(monkeypatch, from_pretrained)
    with client_for(root) as client:
        response = analyse(client)
    assert response.status_code == 200
    bundle = json.loads((root / "reports/result.json").read_text())
    assert bundle["metadata"]["maia2_enabled"] is True
    assert bundle["metadata"]["maia2_available"] is False
    assert "synthetic model cache unavailable" in bundle["metadata"]["maia2_reason"]
    assert bundle["games"][0]["moves"][0]["maia2_played_move_prob"] is None
    assert (root / "reports/result.md").is_file()
    assert caches == [root / "maia2_models"]


@pytest.mark.parametrize("selection", ["default-missing", "explicit-missing", "explicit-existing"])
def test_analysis_preserves_environment_over_selected_file_precedence(tmp_path, monkeypatch, selection):
    root = tmp_path / "project"
    make_project(root)
    selected = None
    if selection != "default-missing":
        write_env_file(replace(default_config(), maia2_game_type="classical"), root / ".env.stockfish")
        selected = tmp_path / "settings/selected.env"
    if selection == "explicit-existing":
        assert selected is not None
        write_env_file(replace(default_config(), stockfish_depth=9, maia2_game_type="blitz"), selected)

    launch = tmp_path / "launch"
    launch.mkdir()
    (launch / ".env.stockfish").write_text("MAIA2_GAME_TYPE=unrelated-invalid-type\n")
    monkeypatch.chdir(launch)
    monkeypatch.setenv("STOCKFISH_DEPTH", "4")
    monkeypatch.setenv("STOCKFISH_TIME_LIMIT", "0.02")
    monkeypatch.setenv("STOCKFISH_PATH", "engines/synthetic-stockfish")
    monkeypatch.setenv("MAIA2_TARGET_ELO", "1300")
    monkeypatch.setenv("MAIA2_ENABLED", "false")
    with client_for(root, selected) as client:
        response = analyse(client)
    assert response.status_code == 200, response.text
    metadata = json.loads((root / "reports/result.json").read_text())["metadata"]
    assert metadata["stockfish_depth"] == 4
    assert metadata["stockfish_time_limit"] == 0.02
    assert metadata["stockfish_path"] == str(root / "engines/synthetic-stockfish")
    assert metadata["maia2_target_elo"] == 1300
    assert metadata["maia2_enabled"] is False
    assert metadata["maia2_game_type"] == ("blitz" if selection == "explicit-existing" else "rapid")
    assert Path.cwd() == launch


@pytest.mark.parametrize("key,value,error_field", [
    ("STOCKFISH_DEPTH", "not-a-number", "config"),
    ("STOCKFISH_DEPTH", "0", "stockfish_depth"),
    ("STOCKFISH_TIME_LIMIT", "not-a-number", "config"),
    ("STOCKFISH_TIME_LIMIT", "0", "stockfish_time_limit"),
    ("MAIA2_TARGET_ELO", "not-a-number", "config"),
    ("MAIA2_TARGET_ELO", "2200", "maia2_target_elo"),
])
def test_missing_file_invalid_environment_is_rejected_before_analysis(tmp_path, monkeypatch, key, value, error_field):
    root = tmp_path / "project"
    make_project(root)
    monkeypatch.setenv(key, value)
    calls = []
    monkeypatch.setattr(pipeline, "analyse_game", lambda game, *_args, **_kwargs: calls.append(game) or analyse_game_mock(game))
    with client_for(root) as client:
        response = analyse(client)
    assert response.status_code == 400
    assert response.json()["ok"] is False
    assert error_field in response.json()["errors"]
    assert calls == []
    assert not (root / "reports").exists()
    assert not (root / "maia2_models").exists()
