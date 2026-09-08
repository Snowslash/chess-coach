"""SYNTHETIC isolated-wheel writable data-root regression."""
from chess_coach import cli


def test_web_cli_accepts_explicit_project_root(monkeypatch, tmp_path):
    calls=[]
    monkeypatch.setattr(cli, "run_web_server", lambda **kwargs: calls.append(kwargs) or 0)
    assert cli.main(["web", "--project-root", str(tmp_path), "--port", "5182"]) == 0
    assert calls[0]["project_root"] == str(tmp_path)
