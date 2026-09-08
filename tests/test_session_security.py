"""SYNTHETIC local-session regressions; no external requests."""
from fastapi.testclient import TestClient
from chess_coach.web_app import create_app


def client_for(path):
    return TestClient(create_app(project_root=path), base_url="http://127.0.0.1")


def test_missing_token_cannot_write_config(tmp_path):
    client = client_for(tmp_path)
    response = client.post("/api/config", json={"default_player": "ExampleUser"})
    assert response.status_code == 403
    assert not (tmp_path / ".env.stockfish").exists()


def test_bootstrap_token_is_per_app_and_required_for_mutations(tmp_path):
    client = client_for(tmp_path)
    bootstrap = client.get("/api/bootstrap")
    assert bootstrap.headers["cache-control"] == "no-store"
    token = bootstrap.json()["session_token"]
    assert len(token) >= 32
    other = client_for(tmp_path / "other").get("/api/bootstrap").json()["session_token"]
    assert token != other
    for wrong in ("", "wrong", other):
        assert client.post("/api/config", json={}, headers={"X-Chess-Coach-Session": wrong}).status_code == 403
    headers = {"X-Chess-Coach-Session": token}
    assert client.post("/api/config", json={}, headers=headers).status_code == 200
    assert (tmp_path / ".env.stockfish").exists()
    assert client.get("/api/config").json()["exists"] is True
    assert client.post("/api/config", json={}, headers={**headers, "Origin": "https://attacker.example"}).status_code == 403
    assert client.get("/api/bootstrap", headers={"Host": "attacker.example"}).status_code == 400
