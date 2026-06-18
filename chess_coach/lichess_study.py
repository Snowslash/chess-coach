from __future__ import annotations

import json
import os
from dataclasses import dataclass
from io import StringIO
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen as default_urlopen

import chess.pgn


class LichessStudyError(RuntimeError):
    pass


class LichessAuthError(LichessStudyError):
    pass


class LichessApiError(LichessStudyError):
    pass


@dataclass(frozen=True)
class StudyRef:
    id: str
    url: str


@dataclass(frozen=True)
class StudyChapterRef:
    id: str
    name: str
    url: str
    status: str | None = None


@dataclass(frozen=True)
class StudyImportResult:
    study_id: str
    study_url: str
    chapters: list[StudyChapterRef]


def token_from_env(name: str = "LICHESS_TOKEN") -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise LichessAuthError(f"Missing Lichess token env var: {name}")
    return value


def bearer_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "User-Agent": "chess-coach/1.0",
    }


def _post_form(
    url: str,
    *,
    token: str,
    form: Mapping[str, str],
    urlopen=default_urlopen,
    timeout: int = 30,
) -> dict[str, Any]:
    body = urlencode(form).encode("utf-8")
    request = Request(url, data=body, headers=bearer_headers(token), method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 429:
            raise LichessApiError(f"Lichess rate limit hit on {url}: {detail}") from exc
        raise LichessApiError(f"Lichess API error {exc.code} on {url}: {detail}") from exc
    except URLError as exc:
        raise LichessApiError(f"Could not reach Lichess: {exc.reason}") from exc
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise LichessApiError(f"Lichess API returned non-JSON response from {url}") from exc


def create_study(
    *,
    token: str,
    name: str,
    visibility: str = "private",
    base_url: str = "https://lichess.org",
    urlopen=default_urlopen,
) -> StudyRef:
    cleaned_name = name.strip()
    if not 2 <= len(cleaned_name) <= 100:
        raise ValueError("Study name must be 2-100 characters")
    if visibility not in {"private", "unlisted"}:
        raise ValueError("Visibility must be one of: private, unlisted")

    payload = _post_form(
        f"{base_url}/api/study",
        token=token,
        form={
            "name": cleaned_name,
            "visibility": visibility,
            "computer": "owner",
            "explorer": "owner",
            "cloneable": "nobody",
            "shareable": "nobody",
            "chat": "nobody",
            "sticky": "true",
        },
        urlopen=urlopen,
    )
    study_id = str(payload.get("id", "")).strip()
    if not study_id:
        raise LichessApiError("Lichess Study creation response missing id")
    return StudyRef(id=study_id, url=f"{base_url}/study/{study_id}")


def count_pgn_games(pgn: str) -> int:
    handle = StringIO(pgn)
    total = 0
    while chess.pgn.read_game(handle) is not None:
        total += 1
    return total


def import_pgn_to_study(
    *,
    token: str,
    study_id: str,
    pgn: str,
    name: str | None = None,
    orientation: str = "white",
    variant: str | None = None,
    mode: str | None = None,
    base_url: str = "https://lichess.org",
    urlopen=default_urlopen,
) -> StudyImportResult:
    if not pgn.strip():
        raise ValueError("PGN must not be empty")
    if orientation not in {"white", "black"}:
        raise ValueError("Orientation must be one of: white, black")
    if mode is not None and mode not in {"practice", "conceal", "gamebook"}:
        raise ValueError("Mode must be one of: practice, conceal, gamebook")

    game_count = count_pgn_games(pgn)
    if game_count == 0:
        raise ValueError("PGN must contain at least one parseable game")
    if game_count > 64:
        raise ValueError(f"PGN contains {game_count} games; Lichess Study limit is 64 chapters")

    form: dict[str, str] = {
        "pgn": pgn,
        "orientation": orientation,
    }
    cleaned_name = name.strip() if name is not None else ""
    if cleaned_name and game_count == 1:
        form["name"] = cleaned_name
    if variant:
        form["variant"] = variant
    if mode:
        form["mode"] = mode

    payload = _post_form(
        f"{base_url}/api/study/{study_id}/import-pgn",
        token=token,
        form=form,
        urlopen=urlopen,
    )

    chapters: list[StudyChapterRef] = []
    for item in payload.get("chapters", []):
        chapter_id = str(item.get("id", "")).strip()
        chapter_name = str(item.get("name", "")).strip()
        if not chapter_id or not chapter_name:
            continue
        chapters.append(
            StudyChapterRef(
                id=chapter_id,
                name=chapter_name,
                url=f"{base_url}/study/{study_id}/{chapter_id}",
                status=item.get("status"),
            )
        )

    return StudyImportResult(
        study_id=study_id,
        study_url=f"{base_url}/study/{study_id}",
        chapters=chapters,
    )
