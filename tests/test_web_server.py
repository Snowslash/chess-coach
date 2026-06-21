from __future__ import annotations

import pytest

from chess_coach import cli
from chess_coach.web_server import guard_host, parse_host_port


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_guard_host_allows_loopback_by_default(host: str):
    assert guard_host(host, allow_lan=False) == host


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "10.0.0.8"])
def test_guard_host_rejects_non_loopback_without_explicit_override(host: str):
    with pytest.raises(ValueError, match="loopback"):
        guard_host(host, allow_lan=False)


def test_guard_host_allows_non_loopback_with_explicit_override():
    assert guard_host("0.0.0.0", allow_lan=True) == "0.0.0.0"


def test_parse_host_port_reads_defaults_from_web_command():
    parser = cli.build_parser()

    args = parser.parse_args(["web"])

    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.open is False
    assert args.allow_lan is False


def test_cli_web_returns_error_for_non_loopback_without_allow_lan(monkeypatch, capsys):
    called = False

    def fake_run_server(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("run_server should not be called")

    monkeypatch.setattr(cli, "run_web_server", fake_run_server)

    code = cli.main(["web", "--host", "0.0.0.0"])

    assert code == 2
    assert called is False
    assert "loopback" in capsys.readouterr().err


def test_cli_web_runs_server_with_open_flag(monkeypatch):
    calls = []

    monkeypatch.setattr(
        cli,
        "run_web_server",
        lambda **kwargs: calls.append(kwargs) or 0,
    )

    code = cli.main(["web", "--port", "9000", "--open"])

    assert code == 0
    assert calls == [
        {
            "host": "127.0.0.1",
            "port": 9000,
            "open_browser": True,
            "allow_lan": False,
            "project_root": None,
            "env_file": None,
        }
    ]
