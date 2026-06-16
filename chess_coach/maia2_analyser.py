from __future__ import annotations

from dataclasses import dataclass
import importlib
import importlib.util
from typing import Callable, Iterable

from .config import ChessCoachConfig
from .models import GameAnalysis

MAIA2_RUNTIME_DEPENDENCIES = ("gdown", "numpy", "pandas", "torch", "tqdm", "einops", "pyzstd", "yaml")


@dataclass(frozen=True)
class Maia2Status:
    enabled: bool
    available: bool
    reason: str | None = None


def maia2_available(config: ChessCoachConfig) -> Maia2Status:
    """Return whether optional Maia 2 human-likeness analysis can run.

    Maia 2 is deliberately optional for the MVP: Stockfish remains the tactical
    analysis engine, and this module only exposes an availability surface until
    we wire position-wise inference into reports.
    """
    if not config.maia2_enabled:
        return Maia2Status(enabled=False, available=False, reason="disabled")
    if importlib.util.find_spec("maia2") is None:
        return Maia2Status(
            enabled=True,
            available=False,
            reason="Python package 'maia2' is not installed. Install it to enable human-likeness analysis.",
        )
    missing = [name for name in MAIA2_RUNTIME_DEPENDENCIES if importlib.util.find_spec(name) is None]
    if missing:
        packages = " ".join(missing)
        return Maia2Status(
            enabled=True,
            available=False,
            reason=f"Maia 2 dependency missing: {packages}. Run: python -m pip install '.[maia2]'",
        )
    return Maia2Status(enabled=True, available=True)


def load_maia2_runtime(config: ChessCoachConfig):
    """Load Maia 2 model/runtime. This may download model weights."""
    maia2_model = importlib.import_module("maia2.model")
    maia2_inference = importlib.import_module("maia2.inference")
    model = maia2_model.from_pretrained(type=config.maia2_game_type, device=config.maia2_device)
    prepared = maia2_inference.prepare()
    return model, prepared, maia2_inference.inference_each


def annotate_games_with_maia2(
    games: Iterable[GameAnalysis],
    model: object,
    prepared: object,
    target_elo: int,
    inference_each: Callable[[object, object, str, int, int], tuple[dict[str, float], float]],
    top_n: int = 3,
) -> None:
    """Annotate the analysed player's moves with Maia 2 probabilities.

    `inference_each` is injected so tests can exercise this without importing
    torch or downloading Maia 2 weights. In production it should be
    `maia2.inference.inference_each`.
    """
    for game in games:
        for move in game.moves:
            if game.player_colour is not None and move.side != game.player_colour:
                continue
            if not move.fen_before:
                continue
            move_probs, win_prob = inference_each(model, prepared, move.fen_before, target_elo, target_elo)
            move.maia2_played_move_prob = move_probs.get(move.uci)
            move.maia2_top_moves = dict(list(move_probs.items())[:top_n])
            move.maia2_win_prob = win_prob
