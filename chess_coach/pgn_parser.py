from __future__ import annotations
from pathlib import Path
import chess, chess.pgn
from .models import ParsedGame, ParsedMove
def _header(headers,key,default="?"):
    v=headers.get(key,default); return v if v not in (None,"") else default
def _player_colour(headers, player):
    if not player: return None
    n=player.strip().casefold()
    if n and n==headers.get("White","").strip().casefold(): return "white"
    if n and n==headers.get("Black","").strip().casefold(): return "black"
    return None
def parse_pgn_file(path:str|Path, player:str|None=None)->list[ParsedGame]:
    p=Path(path); games=[]
    with p.open('r',encoding='utf-8') as h:
        idx=1
        while True:
            g=chess.pgn.read_game(h)
            if g is None: break
            b=g.board(); moves=[]
            for ply,m in enumerate(g.mainline_moves(), start=1):
                side='white' if b.turn==chess.WHITE else 'black'; san=b.san(m)
                moves.append(ParsedMove(move_number=(ply+1)//2, side=side, san=san, uci=m.uci()))
                b.push(m)
            headers={str(k):str(v) for k,v in g.headers.items()}
            games.append(ParsedGame(game_id=f'{p.stem}-{idx}', event=_header(g.headers,'Event'), site=_header(g.headers,'Site'), date=_header(g.headers,'Date'), white=_header(g.headers,'White'), black=_header(g.headers,'Black'), result=_header(g.headers,'Result','*'), player_colour=_player_colour(g.headers,player), headers=headers, moves=moves))
            idx+=1
    return games
