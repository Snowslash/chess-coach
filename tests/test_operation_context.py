"""Synthetic API/service regressions: no network, models or real user data."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
from threading import Event

from fastapi.testclient import TestClient
import pytest

from chess_coach import pipeline, web_app
from chess_coach.config import default_config, write_env_file
from chess_coach.stockfish_analyser import analyse_game_mock


def client_for(root, env_file=None):
    client = TestClient(web_app.create_app(project_root=root, env_file=env_file), base_url="http://127.0.0.1")
    client.headers["X-Chess-Coach-Session"] = client.get("/api/bootstrap").json()["session_token"]
    return client


def prepare_root(root, label):
    (root / "input").mkdir(parents=True)
    (root / "input/game.pgn").write_text(f'[Event "{label}"]\n[White "ExampleUser"]\n\n1. e4 e5 *\n')
    write_env_file(replace(default_config(), stockfish_depth=9), root / ".env.stockfish")


def test_selected_config_reaches_analysis_service(tmp_path, monkeypatch):
    root = tmp_path / "project"
    prepare_root(root, "Selected settings")
    selected = tmp_path / "settings/selected.env"
    write_env_file(replace(default_config(), stockfish_depth=5, stockfish_time_limit=0.02,
                           maia2_target_elo=1300, maia2_game_type="blitz"), selected)
    monkeypatch.setattr(pipeline, "analyse_game", lambda game, cfg, mock: analyse_game_mock(game))

    with client_for(root, selected) as client:
        response = client.post("/api/analyse", json={"username": "ExampleUser", "pgn_path": "input/game.pgn",
                                                   "out_path": "reports/result.md", "mock": True})

    assert response.status_code == 200
    metadata = json.loads((root / "reports/result.json").read_text())["metadata"]
    assert metadata["stockfish_depth"] == 5
    assert metadata["stockfish_time_limit"] == 0.02
    assert metadata["maia2_target_elo"] == 1300
    assert metadata["maia2_game_type"] == "blitz"


def test_overlapping_api_analysis_keeps_paths_config_and_cwd_operation_scoped(tmp_path, monkeypatch):
    roots = {name: tmp_path / name for name in ("First", "Second")}
    entered = {name: Event() for name in roots}
    release = {name: Event() for name in roots}
    seen = {}
    clients = {}
    for index, (name, root) in enumerate(roots.items()):
        prepare_root(root, name)
        selected = root / "settings/selected.env"
        write_env_file(replace(default_config(), stockfish_depth=4 + index,
                               stockfish_time_limit=0.02 + index * 0.01,
                               stockfish_path=f"engines/{name}", maia2_target_elo=1300 + index * 100), selected)
        clients[name] = client_for(root, selected)

    # A legacy cwd race can only damage this disposable launch directory.
    launch = tmp_path / "launch"
    launch.mkdir()
    monkeypatch.chdir(launch)
    real_chdir = os.chdir
    cwd_changes = []

    def record_chdir(path):
        cwd_changes.append(Path(path))
        real_chdir(path)

    def fake_engine_boundary(game, cfg, mock):
        seen[game.event] = (cfg, Path.cwd())
        entered[game.event].set()
        assert release[game.event].wait(5), "test did not release engine boundary"
        return analyse_game_mock(game)

    monkeypatch.setattr(os, "chdir", record_chdir)
    monkeypatch.setattr(pipeline, "analyse_game", fake_engine_boundary)
    payload = {"username": "ExampleUser", "pgn_path": "input/game.pgn", "out_path": "reports/result.md", "mock": True}
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(clients["First"].post, "/api/analyse", json=payload)
            try:
                assert entered["First"].wait(5)
                second = pool.submit(clients["Second"].post, "/api/analyse", json=payload)
                assert entered["Second"].wait(5)
                release["First"].set()
                first_response = first.result(timeout=5)
                release["Second"].set()
                second_response = second.result(timeout=5)
                final_cwd = Path.cwd()
            finally:
                for event in release.values():
                    event.set()
    finally:
        real_chdir(launch)
        for client in clients.values():
            client.close()

    assert cwd_changes == [], "web operations must not change process-global cwd, even temporarily"
    assert final_cwd == launch
    for index, (name, root) in enumerate(roots.items()):
        cfg, observed_cwd = seen[name]
        assert observed_cwd == launch
        assert cfg.stockfish_depth == 4 + index
        assert cfg.stockfish_path == str(root / f"engines/{name}")
        bundle = json.loads((root / "reports/result.json").read_text())
        assert bundle["games"][0]["event"] == name
        assert bundle["metadata"]["stockfish_depth"] == 4 + index
        assert bundle["metadata"]["maia2_target_elo"] == 1300 + index * 100
        assert Path(bundle["source_pgn"]) == root / "input/game.pgn"
        assert "# Chess Coach Report" in (root / "reports/result.md").read_text()
    for response in (first_response, second_response):
        assert response.status_code == 200
        assert response.json() == {"ok": True, "markdown_path": "reports/result.md", "json_path": "reports/result.json",
                                   "games_analysed": 1, "stdout": "Markdown report: reports/result.md\nStructured JSON: reports/result.json", "stderr": ""}
    assert not (launch / "reports").exists()


def test_import_and_export_use_resolved_paths_without_chdir(tmp_path, monkeypatch):
    root = tmp_path / "project"
    prepare_root(root, "Synthetic")
    original_cwd = Path.cwd()
    cwd_changes = []
    real_chdir = os.chdir
    monkeypatch.setattr(os, "chdir", lambda path: (cwd_changes.append(Path(path)), real_chdir(path))[-1])
    imported_paths = []

    def fake_fetch(_username, out_path, **_kwargs):
        imported_paths.append((out_path, Path.cwd()))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text('1. d4 d5 *\n')
        return out_path

    monkeypatch.setattr(web_app, "fetch_recent_games", fake_fetch)
    with client_for(root) as client:
        imported = client.post("/api/import-lichess", json={"username": "ExampleUser", "out_path": "input/imported.pgn"})
        analysed = client.post("/api/analyse", json={"username": "ExampleUser", "pgn_path": "input/imported.pgn",
                                                   "out_path": "reports/result.md", "mock": True})
        exported = client.post("/api/export-annotated-pgn", json={"json_path": "reports/result.json",
                                                                "out_path": "reports/annotated/result.pgn"})
    assert imported.status_code == analysed.status_code == exported.status_code == 200
    assert cwd_changes == []
    assert Path.cwd() == original_cwd
    assert imported_paths == [(root / "input/imported.pgn", original_cwd)]
    assert imported.json() == {"ok": True, "out_path": "input/imported.pgn", "stdout": "Imported Lichess PGN: input/imported.pgn", "stderr": ""}
    assert exported.json()["out_path"] == "reports/annotated/result.pgn"
    assert "1. d4 d5" in (root / "reports/annotated/result.pgn").read_text()


@pytest.mark.parametrize("setting", ["STOCKFISH_DEPTH=0", "STOCKFISH_DEPTH=not-a-number"])
def test_invalid_selected_analysis_config_is_rejected_before_engine_or_outputs(tmp_path, monkeypatch, setting):
    root = tmp_path / "project"
    prepare_root(root, "Synthetic")
    selected = root / "selected.env"
    selected.write_text(setting + '\n')
    calls = []
    monkeypatch.setattr(pipeline, "analyse_game", lambda *args, **kwargs: calls.append(args) or analyse_game_mock(args[0]))
    with client_for(root, selected) as client:
        response = client.post("/api/analyse", json={"username": "ExampleUser", "pgn_path": "input/game.pgn",
                                                   "out_path": "reports/result.md", "mock": True})
    assert response.status_code == 400
    assert response.json()["ok"] is False
    assert response.json()["errors"]
    assert calls == []
    assert not (root / "reports").exists()


@pytest.mark.parametrize("field", ["pgn_path", "out_path", "derived_json"])
def test_analysis_rejects_symlink_escape_including_derived_json(tmp_path, field):
    root = tmp_path / "project"
    prepare_root(root, "Synthetic")
    outside = tmp_path / "outside"
    outside.mkdir()
    protected = outside / "protected"
    protected.write_text('1. e4 *\n')
    payload = {"username": "ExampleUser", "pgn_path": "input/game.pgn", "out_path": "reports/result.md", "mock": True}
    (root / "reports").mkdir()
    link = root / ("reports/result.json" if field == "derived_json" else payload[field])
    if link.exists():
        link.unlink()
    link.symlink_to(protected)
    with client_for(root) as client:
        response = client.post("/api/analyse", json=payload)
    assert response.status_code == 400
    assert protected.read_text() == '1. e4 *\n'
    assert not (root / "reports/result.md").exists() or field == "out_path"
