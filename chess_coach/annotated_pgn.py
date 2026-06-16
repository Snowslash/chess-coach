from __future__ import annotations

import re
from io import StringIO

import chess
import chess.pgn

from .models import AnalysisBundle, CriticalMoment, GameAnalysis, MoveAnalysis

_HEADER_KEYS = ("Event", "Site", "Date", "White", "Black", "Result")


def _clean_comment_text(text: str) -> str:
    text = text.replace("{", "(").replace("}", ")")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _first_useful_text(*values: str | None) -> str | None:
    for value in values:
        if value:
            cleaned = _clean_comment_text(value)
            if cleaned:
                return cleaned
    return None


def _best_move_display(board: chess.Board, raw_best_move: str | None) -> str | None:
    if not raw_best_move:
        return None
    try:
        move = chess.Move.from_uci(raw_best_move)
    except ValueError:
        return _clean_comment_text(raw_best_move)
    if move not in board.legal_moves:
        return _clean_comment_text(raw_best_move)
    return board.san(move)


def format_move_comment(
    move: MoveAnalysis,
    critical: CriticalMoment | None = None,
    *,
    best_move_display: str | None = None,
) -> str:
    classification = critical.classification if critical else move.classification
    eval_change = critical.eval_change if critical and critical.eval_change is not None else move.eval_change
    best_move = best_move_display
    if not best_move:
        best_move = critical.best_move if critical and critical.best_move else move.best_move
    note = _first_useful_text(critical.note if critical else None, move.note)

    details: list[str] = []
    if classification != "book/neutral":
        details.append(classification)
    if eval_change is not None:
        details.append(f"eval swing {eval_change:+.2f}")
    if best_move:
        details.append(f"Best: {_clean_comment_text(best_move)}")
    if move.maia2_played_move_prob is not None:
        details.append(f"Maia2: played move {move.maia2_played_move_prob * 100:.1f}%")
    if note:
        details.append(note)

    if not details:
        return "Chess Coach: reviewed move."
    return f"Chess Coach: {'; '.join(details)}."


def _critical_lookup(game: GameAnalysis) -> dict[tuple[int, str], CriticalMoment]:
    return {(moment.move_number, moment.side): moment for moment in game.critical_moments}


def _starting_board(analysis: GameAnalysis) -> chess.Board:
    fen = analysis.headers.get("FEN")
    if fen:
        try:
            return chess.Board(fen)
        except ValueError as exc:
            raise ValueError(f"Invalid starting FEN for {analysis.game_id}: {fen}") from exc
    return chess.Board()


def _should_comment(
    move: MoveAnalysis,
    critical: CriticalMoment | None,
    *,
    critical_only: bool,
    include_all_moves: bool,
) -> bool:
    if critical is not None:
        return True
    if include_all_moves:
        return True
    if critical_only:
        return False
    return any(
        [
            move.classification != "book/neutral",
            move.note is not None,
            move.maia2_played_move_prob is not None,
        ]
    )


def render_annotated_game(
    analysis: GameAnalysis,
    *,
    critical_only: bool = True,
    include_all_moves: bool = False,
) -> chess.pgn.Game:
    game = chess.pgn.Game()
    defaults = {
        "Event": analysis.event,
        "Site": analysis.site,
        "Date": analysis.date,
        "White": analysis.white,
        "Black": analysis.black,
        "Result": analysis.result,
    }
    for key in _HEADER_KEYS:
        value = defaults.get(key)
        if value:
            game.headers[key] = value
    for key, value in analysis.headers.items():
        if value:
            game.headers[key] = value

    board = _starting_board(analysis)
    if analysis.headers.get("FEN"):
        game.setup(board.copy(stack=False))
    node = game
    criticals = _critical_lookup(analysis)

    for analysed_move in analysis.moves:
        try:
            move = chess.Move.from_uci(analysed_move.uci)
        except ValueError as exc:
            raise ValueError(f"Invalid UCI move for {analysis.game_id}: {analysed_move.uci}") from exc
        if move not in board.legal_moves:
            raise ValueError(
                f"Illegal move for {analysis.game_id} at {analysed_move.move_number} {analysed_move.side}: {analysed_move.uci}"
            )

        critical = criticals.get((analysed_move.move_number, analysed_move.side))
        best_move_display = _best_move_display(board, critical.best_move if critical else analysed_move.best_move)

        node = node.add_variation(move)
        board.push(move)

        if _should_comment(
            analysed_move,
            critical,
            critical_only=critical_only,
            include_all_moves=include_all_moves,
        ):
            node.comment = format_move_comment(analysed_move, critical, best_move_display=best_move_display)

    return game


def count_games_to_export(bundle: AnalysisBundle, *, max_games: int | None = None) -> int:
    if max_games is not None and max_games < 0:
        raise ValueError("--max-games must be >= 0")
    games = bundle.games[:max_games] if max_games is not None else bundle.games
    return len(games)


def render_annotated_pgn(
    bundle: AnalysisBundle,
    *,
    max_games: int | None = None,
    critical_only: bool = True,
    include_all_moves: bool = False,
) -> str:
    if max_games is not None and max_games < 0:
        raise ValueError("--max-games must be >= 0")
    games = bundle.games[:max_games] if max_games is not None else bundle.games
    rendered_games = [
        render_annotated_game(
            game,
            critical_only=critical_only,
            include_all_moves=include_all_moves,
        ).accept(chess.pgn.StringExporter(headers=True, variations=False, comments=True))
        for game in games
    ]
    if not rendered_games:
        return ""
    handle = StringIO()
    handle.write("\n\n".join(rendered_games))
    handle.write("\n")
    return handle.getvalue()
