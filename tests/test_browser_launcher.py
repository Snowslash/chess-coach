"""SYNTHETIC launcher arguments; no browser or server started."""
import runpy
import sys
from pathlib import Path
from chess_coach import cli, web_server


def test_browser_launcher_uses_writable_cwd_not_frozen_package(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "main", lambda args: calls.append(args) or 0)
    monkeypatch.setattr(web_server, "run_web_server", lambda **kwargs: 0)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["chess-coach-browser"])
    script = Path(__file__).resolve().parents[1] / "scripts/run_web_gui.py"
    with __import__("pytest").raises(SystemExit) as result:
        runpy.run_path(str(script), run_name="__main__")
    assert result.value.code == 0
    assert calls == [["web", "--project-root", str(tmp_path), "--open"]]


def test_browser_launcher_retains_explicit_port_and_cli_options(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "main", lambda args: calls.append(args) or 0)
    monkeypatch.setattr(web_server, "run_web_server", lambda **kwargs: 0)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["chess-coach-browser", "--port", "5182"])
    script = Path(__file__).resolve().parents[1] / "scripts/run_web_gui.py"
    with __import__("pytest").raises(SystemExit):
        runpy.run_path(str(script), run_name="__main__")
    assert calls == [["web", "--project-root", str(tmp_path), "--port", "5182"]]
