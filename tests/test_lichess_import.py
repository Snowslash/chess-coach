from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from chess_coach.lichess_import import fetch_recent_games


class FakeResponse:
    def __init__(self, body: str):
        self.body = body.encode("utf-8")
        self.headers = {"content-type": "application/x-chess-pgn"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.body


def test_fetch_recent_games_writes_pgn_from_lichess_api(tmp_path: Path):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, dict(request.header_items()), timeout))
        return FakeResponse('[Event "Rated rapid game"]\n\n1. e4 e5 *\n')

    out = tmp_path / "recent.pgn"

    written = fetch_recent_games("exampleuser", out, max_games=5, urlopen=fake_urlopen)

    assert written == out
    assert out.read_text(encoding="utf-8").startswith('[Event "Rated rapid game"]')
    url, headers, timeout = calls[0]
    assert url.startswith("https://lichess.org/api/games/user/exampleuser?")
    assert "max=5" in url
    assert "pgnInJson=false" in url
    assert headers["Accept"] == "application/x-chess-pgn"
    assert headers["User-agent"].startswith("hermes-chess-coach")
    assert timeout == 30


def test_fetch_recent_games_rejects_empty_response(tmp_path: Path):
    def fake_urlopen(request, timeout):
        return FakeResponse("\n")

    with pytest.raises(RuntimeError, match="No PGN data"):
        fetch_recent_games("exampleuser", tmp_path / "empty.pgn", urlopen=fake_urlopen)



def test_fetch_recent_games_includes_optional_filters(tmp_path: Path):
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, timeout))
        return FakeResponse('[Event "Rated rapid game"]\n\n1. e4 e5 *\n')

    out = tmp_path / "recent.pgn"

    fetch_recent_games(
        "exampleuser",
        out,
        max_games=20,
        perf="rapid",
        rated_only=True,
        since_days=14,
        urlopen=fake_urlopen,
        now_millis=lambda: 1_700_000_000_000,
    )

    url, timeout = calls[0]
    query = parse_qs(urlparse(url).query)

    assert query["max"] == ["20"]
    assert query["perfType"] == ["rapid"]
    assert query["rated"] == ["true"]
    assert query["since"] == [str(1_700_000_000_000 - 14 * 24 * 60 * 60 * 1000)]
    assert timeout == 30
