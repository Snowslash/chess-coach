from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .models import AnalysisBundle, GameAnalysis
from .openings import opening_family_from_game


class GameHistoryEntry(BaseModel):
    key: str
    game_id: str
    site: str = "?"
    date: str = "?"
    white: str = "?"
    black: str = "?"
    result: str = "*"
    player_colour: str | None = None
    analysed_at: datetime = Field(default_factory=datetime.now)
    critical_moments: int = 0
    classification_counts: dict[str, int] = Field(default_factory=dict)
    phase_counts: dict[str, int] = Field(default_factory=dict)
    side_counts: dict[str, int] = Field(default_factory=dict)
    opening_family: str | None = None


class PatternHistoryEntry(BaseModel):
    pattern_id: str
    label: str
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)
    occurrences: int = 0
    example_game_keys: list[str] = Field(default_factory=list)
    trend: Literal["new", "improving", "stable", "worsening"] = "new"


class RunHistoryEntry(BaseModel):
    run_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    source_pgn: str = ""
    game_keys: list[str] = Field(default_factory=list)
    games_analysed: int = 0
    critical_moments: int = 0
    top_patterns: list[str] = Field(default_factory=list)


class CoachState(BaseModel):
    schema_version: int = 1
    games: dict[str, GameHistoryEntry] = Field(default_factory=dict)
    patterns: dict[str, PatternHistoryEntry] = Field(default_factory=dict)
    runs: list[RunHistoryEntry] = Field(default_factory=list)


_LICHESS_RE = re.compile(r"lichess\.org/(?:game/export/)?([A-Za-z0-9]{3,12})")
DEFAULT_STATE_PATH = Path(".coach/state.json")


def load_state(path: str | Path = DEFAULT_STATE_PATH) -> CoachState:
    path = Path(path)
    if not path.exists():
        return CoachState()
    return CoachState.model_validate_json(path.read_text(encoding="utf-8"))


def save_state(state: CoachState, path: str | Path = DEFAULT_STATE_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return path


def history_entry_from_game(game: GameAnalysis) -> GameHistoryEntry:
    classification_counts = Counter(moment.classification for moment in game.critical_moments)
    phase_counts = Counter(moment.phase for moment in game.critical_moments)
    side_counts = Counter(moment.side for moment in game.critical_moments)
    return GameHistoryEntry(
        key=game_history_key(game),
        game_id=game.game_id,
        site=game.site,
        date=game.date,
        white=game.white,
        black=game.black,
        result=game.result,
        player_colour=game.player_colour,
        critical_moments=len(game.critical_moments),
        classification_counts=dict(classification_counts),
        phase_counts=dict(phase_counts),
        side_counts=dict(side_counts),
        opening_family=opening_family_from_game(game),
    )


def update_state_from_bundle(state: CoachState, bundle: AnalysisBundle) -> CoachState:
    updated = state.model_copy(deep=True)
    game_keys: list[str] = []

    for game in bundle.games:
        entry = history_entry_from_game(game)
        updated.games[entry.key] = entry
        game_keys.append(entry.key)

    digest = hashlib.sha256(bundle.source_pgn.encode("utf-8")).hexdigest()[:12]
    updated.runs.append(
        RunHistoryEntry(
            run_id=f"{bundle.generated_at.strftime('%Y%m%d%H%M%S')}-{digest}",
            generated_at=bundle.generated_at,
            source_pgn=bundle.source_pgn,
            game_keys=game_keys,
            games_analysed=len(bundle.games),
            critical_moments=sum(len(game.critical_moments) for game in bundle.games),
            top_patterns=(bundle.patterns.training_priorities or bundle.patterns.recurring_weaknesses)[:3],
        )
    )
    return updated


def game_history_key(game: GameAnalysis) -> str:
    site = game.site or game.headers.get("Site", "")
    match = _LICHESS_RE.search(site)
    if match:
        return f"lichess:{match.group(1)}"

    raw = "|".join(
        [
            game.game_id,
            game.date,
            game.white,
            game.black,
            game.result,
            str(len(game.moves)),
        ]
    )
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"pgn:{digest}"



def filter_new_games(games: list[GameAnalysis], state: CoachState) -> list[GameAnalysis]:
    return [game for game in games if game_history_key(game) not in state.games]
