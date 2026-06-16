from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen as default_urlopen


def _current_time_millis() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def fetch_recent_games(
    username: str,
    out_path: str | Path,
    max_games: int = 20,
    perf: str | None = None,
    rated_only: bool = False,
    since_days: int | None = None,
    urlopen=default_urlopen,
    now_millis=_current_time_millis,
) -> Path:
    query: dict[str, str | int] = {
        "max": max_games,
        "pgnInJson": "false",
        "clocks": "true",
        "evals": "false",
        "opening": "true",
    }
    if perf:
        query["perfType"] = perf
    if rated_only:
        query["rated"] = "true"
    if since_days is not None:
        query["since"] = now_millis() - since_days * 24 * 60 * 60 * 1000

    params = urlencode(query)
    url = f"https://lichess.org/api/games/user/{username}?{params}"
    request = Request(
        url,
        headers={
            "Accept": "application/x-chess-pgn",
            "User-Agent": "hermes-chess-coach/0.5",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch recent Lichess games for {username}: {exc}") from exc

    if not body.strip():
        raise RuntimeError(f"No PGN data returned for Lichess user {username}.")

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path
