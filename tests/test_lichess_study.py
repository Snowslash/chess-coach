from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs

import pytest

from chess_coach.lichess_study import (
    LichessApiError,
    LichessAuthError,
    _post_form,
    bearer_headers,
    count_pgn_games,
    create_study,
    import_pgn_to_study,
    token_from_env,
)

SINGLE_GAME_PGN = '[Event "Game 1"]\n[Site "https://lichess.org/abc"]\n[White "White"]\n[Black "Black"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n'
MULTI_GAME_PGN = (
    '[Event "Game 1"]\n[White "White"]\n[Black "Black"]\n[Result "1-0"]\n\n1. e4 e5 1-0\n\n'
    '[Event "Game 2"]\n[White "White2"]\n[Black "Black2"]\n[Result "0-1"]\n\n1. d4 d5 0-1\n'
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


class RecordingUrlopen:
    def __init__(self, body: str = '{"id": "study123"}'):
        self.body = body
        self.calls: list[tuple[object, int]] = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        return FakeResponse(self.body)



def test_token_from_env_returns_value(monkeypatch):
    monkeypatch.setenv("LICHESS_TOKEN", "secret-token")

    assert token_from_env() == "secret-token"


def test_token_from_env_rejects_missing_value(monkeypatch):
    monkeypatch.delenv("LICHESS_TOKEN", raising=False)

    with pytest.raises(LichessAuthError, match="Missing Lichess token env var: LICHESS_TOKEN"):
        token_from_env()


def test_auth_error_does_not_include_token_value(monkeypatch):
    monkeypatch.setenv("LICHESS_TOKEN", "   ")

    with pytest.raises(LichessAuthError) as excinfo:
        token_from_env()

    assert "LICHESS_TOKEN" in str(excinfo.value)
    assert "secret-token" not in str(excinfo.value)


def test_bearer_headers_include_expected_http_headers():
    headers = bearer_headers("secret-token")

    assert headers == {
        "Authorization": "Bearer secret-token",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "chess-coach/1.0",
    }


def test_post_form_uses_post_form_encoding_and_default_timeout():
    recorder = RecordingUrlopen('{"id": "study123"}')

    result = _post_form(
        "https://lichess.org/api/study",
        token="super-secret-token",
        form={"name": "Chess Coach Review", "visibility": "private"},
        urlopen=recorder,
    )

    assert result == {"id": "study123"}
    request, timeout = recorder.calls[0]
    assert request.full_url == "https://lichess.org/api/study"
    assert request.get_method() == "POST"
    assert request.data.decode("utf-8") == "name=Chess+Coach+Review&visibility=private"
    assert timeout == 30


def test_post_form_includes_http_400_response_text_without_token():
    token = "super-secret-token"

    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=BytesIO(b"visibility invalid"),
        )

    with pytest.raises(LichessApiError) as excinfo:
        _post_form(
            "https://lichess.org/api/study",
            token=token,
            form={"name": "Chess Coach Review"},
            urlopen=fake_urlopen,
        )

    assert "Lichess API error 400 on https://lichess.org/api/study: visibility invalid" == str(excinfo.value)
    assert token not in str(excinfo.value)


def test_post_form_mentions_rate_limit_for_http_429():
    token = "super-secret-token"

    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            hdrs=None,
            fp=BytesIO(b"try again later"),
        )

    with pytest.raises(LichessApiError) as excinfo:
        _post_form(
            "https://lichess.org/api/study",
            token=token,
            form={"name": "Chess Coach Review"},
            urlopen=fake_urlopen,
        )

    message = str(excinfo.value)
    assert "Lichess rate limit hit on https://lichess.org/api/study: try again later" == message
    assert token not in message


def test_post_form_wraps_url_error_without_token():
    token = "super-secret-token"

    def fake_urlopen(request, timeout):
        raise URLError("temporary failure")

    with pytest.raises(LichessApiError) as excinfo:
        _post_form(
            "https://lichess.org/api/study",
            token=token,
            form={"name": "Chess Coach Review"},
            urlopen=fake_urlopen,
        )

    assert "Could not reach Lichess: temporary failure" == str(excinfo.value)
    assert token not in str(excinfo.value)


def test_post_form_wraps_non_json_success_without_token():
    token = "super-secret-token"
    recorder = RecordingUrlopen("<html>not json</html>")

    with pytest.raises(LichessApiError) as excinfo:
        _post_form(
            "https://lichess.org/api/study",
            token=token,
            form={"name": "Chess Coach Review"},
            urlopen=recorder,
        )

    message = str(excinfo.value)
    assert "Lichess API returned non-JSON response from https://lichess.org/api/study" == message
    assert token not in message


def test_create_study_posts_required_safe_defaults():
    recorder = RecordingUrlopen('{"id": "study123"}')

    study = create_study(
        token="super-secret-token",
        name="Chess Coach Review 2026-06-17",
        urlopen=recorder,
    )

    request, timeout = recorder.calls[0]
    form = parse_qs(request.data.decode("utf-8"), keep_blank_values=True)

    assert request.full_url == "https://lichess.org/api/study"
    assert request.get_method() == "POST"
    assert timeout == 30
    assert form == {
        "name": ["Chess Coach Review 2026-06-17"],
        "visibility": ["private"],
        "computer": ["owner"],
        "explorer": ["owner"],
        "cloneable": ["nobody"],
        "shareable": ["nobody"],
        "chat": ["nobody"],
        "sticky": ["true"],
    }
    assert study.id == "study123"
    assert study.url == "https://lichess.org/study/study123"


def test_create_study_allows_unlisted_visibility():
    recorder = RecordingUrlopen('{"id": "study123"}')

    create_study(
        token="super-secret-token",
        name="Chess Coach Review 2026-06-17",
        visibility="unlisted",
        urlopen=recorder,
    )

    request, _timeout = recorder.calls[0]
    form = parse_qs(request.data.decode("utf-8"), keep_blank_values=True)
    assert form["visibility"] == ["unlisted"]


def test_create_study_rejects_public_visibility_by_default():
    with pytest.raises(ValueError, match="Visibility must be one of: private, unlisted"):
        create_study(token="super-secret-token", name="Chess Coach Review", visibility="public")


def test_create_study_rejects_too_short_or_too_long_name():
    with pytest.raises(ValueError, match="Study name must be 2-100 characters"):
        create_study(token="super-secret-token", name="x")

    with pytest.raises(ValueError, match="Study name must be 2-100 characters"):
        create_study(token="super-secret-token", name="x" * 101)


def test_create_study_rejects_missing_id_in_response():
    recorder = RecordingUrlopen("{}")

    with pytest.raises(LichessApiError, match="Lichess Study creation response missing id"):
        create_study(token="super-secret-token", name="Chess Coach Review", urlopen=recorder)


def test_count_pgn_games_uses_python_chess_parser():
    assert count_pgn_games(SINGLE_GAME_PGN) == 1
    assert count_pgn_games(MULTI_GAME_PGN) == 2


def test_import_pgn_posts_to_study_import_endpoint():
    recorder = RecordingUrlopen('{"chapters": [{"id": "chap1", "name": "Chapter 1", "status": "1-0"}]}')

    result = import_pgn_to_study(
        token="super-secret-token",
        study_id="abc123",
        pgn=SINGLE_GAME_PGN,
        orientation="white",
        urlopen=recorder,
    )

    request, timeout = recorder.calls[0]
    form = parse_qs(request.data.decode("utf-8"), keep_blank_values=True)

    assert request.full_url == "https://lichess.org/api/study/abc123/import-pgn"
    assert request.get_method() == "POST"
    assert timeout == 30
    assert form["pgn"] == [SINGLE_GAME_PGN]
    assert form["orientation"] == ["white"]
    assert result.study_id == "abc123"
    assert result.study_url == "https://lichess.org/study/abc123"


def test_import_pgn_includes_optional_single_chapter_name():
    recorder = RecordingUrlopen('{"chapters": [{"id": "chap1", "name": "My Chapter"}]}')

    import_pgn_to_study(
        token="super-secret-token",
        study_id="abc123",
        pgn=SINGLE_GAME_PGN,
        name="My Chapter",
        orientation="black",
        variant="standard",
        mode="practice",
        urlopen=recorder,
    )

    request, _timeout = recorder.calls[0]
    form = parse_qs(request.data.decode("utf-8"), keep_blank_values=True)

    assert form["name"] == ["My Chapter"]
    assert form["orientation"] == ["black"]
    assert form["variant"] == ["standard"]
    assert form["mode"] == ["practice"]


def test_import_pgn_omits_name_for_multi_game_pgn():
    recorder = RecordingUrlopen('{"chapters": [{"id": "chap1", "name": "Game 1"}, {"id": "chap2", "name": "Game 2"}]}')

    import_pgn_to_study(
        token="super-secret-token",
        study_id="abc123",
        pgn=MULTI_GAME_PGN,
        name="Ignored Chapter Name",
        urlopen=recorder,
    )

    request, _timeout = recorder.calls[0]
    form = parse_qs(request.data.decode("utf-8"), keep_blank_values=True)

    assert "name" not in form


def test_import_pgn_rejects_invalid_orientation():
    with pytest.raises(ValueError, match="Orientation must be one of: white, black"):
        import_pgn_to_study(
            token="super-secret-token",
            study_id="abc123",
            pgn=SINGLE_GAME_PGN,
            orientation="sideways",
        )


def test_import_pgn_rejects_invalid_mode():
    with pytest.raises(ValueError, match="Mode must be one of: practice, conceal, gamebook"):
        import_pgn_to_study(
            token="super-secret-token",
            study_id="abc123",
            pgn=SINGLE_GAME_PGN,
            mode="analysis",
        )


def test_import_pgn_rejects_empty_pgn_before_request():
    recorder = RecordingUrlopen('{"chapters": []}')

    with pytest.raises(ValueError, match="PGN must not be empty"):
        import_pgn_to_study(token="super-secret-token", study_id="abc123", pgn="   ", urlopen=recorder)

    assert recorder.calls == []


def test_import_pgn_rejects_unparseable_pgn_before_request():
    recorder = RecordingUrlopen('{"chapters": []}')

    with pytest.raises(ValueError, match="PGN must contain at least one parseable game"):
        import_pgn_to_study(token="super-secret-token", study_id="abc123", pgn="%%%%", urlopen=recorder)

    assert recorder.calls == []


def test_import_pgn_rejects_more_than_64_games_before_request():
    recorder = RecordingUrlopen('{"chapters": []}')
    large_pgn = "\n\n".join(
        f'[Event "Game {index}"]\n[White "White"]\n[Black "Black"]\n[Result "1-0"]\n\n1. e4 e5 1-0'
        for index in range(65)
    )

    with pytest.raises(ValueError, match="PGN contains 65 games; Lichess Study limit is 64 chapters"):
        import_pgn_to_study(token="super-secret-token", study_id="abc123", pgn=large_pgn, urlopen=recorder)

    assert recorder.calls == []


def test_import_pgn_returns_created_chapter_refs():
    recorder = RecordingUrlopen(
        '{"chapters": ['
        '{"id": "chap1", "name": "Game 1", "status": "1-0"}, '
        '{"id": "chap2", "name": "Game 2", "status": "0-1"}'
        ']}'
    )

    result = import_pgn_to_study(
        token="super-secret-token",
        study_id="abc123",
        pgn=MULTI_GAME_PGN,
        urlopen=recorder,
    )

    assert result.study_id == "abc123"
    assert result.study_url == "https://lichess.org/study/abc123"
    assert [(chapter.id, chapter.name, chapter.url, chapter.status) for chapter in result.chapters] == [
        ("chap1", "Game 1", "https://lichess.org/study/abc123/chap1", "1-0"),
        ("chap2", "Game 2", "https://lichess.org/study/abc123/chap2", "0-1"),
    ]


def test_import_pgn_surfaces_429_rate_limit():
    token = "super-secret-token"

    def fake_urlopen(request, timeout):
        raise HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            hdrs=None,
            fp=BytesIO(b"slow down"),
        )

    with pytest.raises(LichessApiError, match="Lichess rate limit hit"):
        import_pgn_to_study(
            token=token,
            study_id="abc123",
            pgn=SINGLE_GAME_PGN,
            urlopen=fake_urlopen,
        )
