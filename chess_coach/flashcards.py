from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel

from .models import AnalysisBundle, CriticalMoment, GameAnalysis


class ReviewCard(BaseModel):
    card_id: str
    game_id: str
    move_number: int
    side: str
    phase: str
    theme: str
    fen: str
    actual_move: str
    best_move: str | None = None
    classification: str
    eval_change: float | None = None
    explanation: str | None = None
    review_prompt: str


def _theme_for(moment: CriticalMoment) -> str:
    if moment.classification == "blunder":
        return "tactical_blunder"
    if moment.classification == "missed win":
        return "missed_win"
    if moment.classification == "tactical miss":
        return "tactical_miss"
    return f"{moment.phase}_{moment.classification.replace(' ', '_')}"


def _review_prompt(moment: CriticalMoment) -> str:
    return (
        f"What cue before move {moment.move_number} could have warned you against {moment.san}, "
        f"and what candidate move would you compare with {moment.best_move or 'the engine choice'}?"
    )


def _card_id(game: GameAnalysis, moment: CriticalMoment) -> str:
    raw = f"{game.game_id}|{moment.move_number}|{moment.side}|{moment.san}|{moment.fen_before}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"card:{digest}"


def _cards_from_game(game: GameAnalysis) -> Iterable[ReviewCard]:
    for moment in game.critical_moments:
        if not moment.fen_before:
            continue
        yield ReviewCard(
            card_id=_card_id(game, moment),
            game_id=game.game_id,
            move_number=moment.move_number,
            side=moment.side,
            phase=moment.phase,
            theme=_theme_for(moment),
            fen=moment.fen_before,
            actual_move=moment.san,
            best_move=moment.best_move,
            classification=moment.classification,
            eval_change=moment.eval_change,
            explanation=moment.note,
            review_prompt=_review_prompt(moment),
        )


def cards_from_bundle(bundle: AnalysisBundle) -> list[ReviewCard]:
    cards: list[ReviewCard] = []
    for game in bundle.games:
        cards.extend(_cards_from_game(game))
    return cards


def write_cards_markdown(cards: list[ReviewCard], out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Chess Coach Review Cards", ""]
    if not cards:
        lines.extend(["No review cards were generated.", ""])
    for index, card in enumerate(cards, start=1):
        lines.extend(
            [
                f"## Card {index} — {card.theme}",
                "",
                f"- Game: {card.game_id}",
                f"- Move: {card.move_number}",
                f"- Side: {card.side}",
                f"- Phase: {card.phase}",
                f"- Classification: {card.classification}",
                f"- Eval change: {card.eval_change}",
                f"- FEN: `{card.fen}`",
                f"- Actual move: {card.actual_move}",
                f"- Best move: {card.best_move or 'Unknown'}",
                "",
                "### Explanation",
                card.explanation or "No explanation recorded.",
                "",
                "### Review prompt",
                card.review_prompt,
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
