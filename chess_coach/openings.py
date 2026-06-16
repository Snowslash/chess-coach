from __future__ import annotations

from .models import GameAnalysis



def opening_family_from_game(game: GameAnalysis, plies: int = 8) -> str | None:
    sans = [move.san for move in game.moves[:plies] if move.san]
    return " ".join(sans) if sans else None
