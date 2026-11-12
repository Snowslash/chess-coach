from __future__ import annotations

from pathlib import Path
from typing import Mapping

import chess
import chess.pgn

from .models import ParsedGame, ParsedMove


def starting_board(headers: Mapping[str, str]) -> chess.Board:
    """Use the PGN FEN when present, otherwise the ordinary standard position.

    Match python-chess's FEN handling (including FEN without SetUp), but never
    silently analyse another variant using the standard-chess engine pipeline.
    """
    variant = headers.get("Variant", "Standard")
    if variant.casefold() not in {alias.casefold() for alias in chess.Board.aliases}:
        raise ValueError(f"Unsupported variant: {variant}. Only standard chess is supported.")
    board = chess.Board(headers.get("FEN", chess.STARTING_FEN))
    if board.has_chess960_castling_rights():
        raise ValueError("Unsupported Chess960 starting position. Only standard chess is supported.")
    return board


def _header(headers,key,default="?"):
    v=headers.get(key,default); return v if v not in (None,"") else default
def _player_colour(headers, player):
    if not player: return None
    n=player.strip().casefold()
    if n and n==headers.get("White","").strip().casefold(): return "white"
    if n and n==headers.get("Black","").strip().casefold(): return "black"
    return None
def parse_pgn_file(path: str | Path, player: str | None = None) -> list[ParsedGame]:
    path = Path(path)
    games = []
    with path.open('r', encoding='utf-8') as handle:
        index = 1
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            board = starting_board(game.headers)
            moves = []
            for move in game.mainline_moves():
                moves.append(ParsedMove(
                    move_number=board.fullmove_number,
                    side='white' if board.turn == chess.WHITE else 'black',
                    san=board.san(move),
                    uci=move.uci(),
                ))
                board.push(move)
            headers = {str(key): str(value) for key, value in game.headers.items()}
            games.append(ParsedGame(
                game_id=f'{path.stem}-{index}',
                event=_header(game.headers, 'Event'),
                site=_header(game.headers, 'Site'),
                date=_header(game.headers, 'Date'),
                white=_header(game.headers, 'White'),
                black=_header(game.headers, 'Black'),
                result=_header(game.headers, 'Result', '*'),
                player_colour=_player_colour(game.headers, player),
                headers=headers,
                moves=moves,
            ))
            index += 1
    return games
