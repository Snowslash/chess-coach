from __future__ import annotations
import shutil
from pathlib import Path
import chess, chess.engine
from .config import ChessCoachConfig
from .models import CriticalMoment, GameAnalysis, MoveAnalysis, ParsedGame
CRITICAL_CLASSIFICATIONS={"inaccuracy","mistake","blunder","missed win","tactical miss"}
def stockfish_available(config:ChessCoachConfig):
    c=config.stockfish_path or shutil.which('stockfish')
    if not c: return False,None
    return ((Path(c).exists() or shutil.which(c) is not None), c)
def phase_for_move(n:int): return 'opening' if n<=10 else ('endgame' if n>=31 else 'middlegame')
def classify_eval_loss(loss:float, san:str=''):
    if loss>2.0: return 'blunder'
    if loss>1.0: return 'mistake'
    if loss>0.5: return 'inaccuracy'
    if san.endswith('??'): return 'tactical miss'
    return 'book/neutral'
def _critical(gid, m): return CriticalMoment(game_id=gid, move_number=m.move_number, side=m.side, san=m.san, phase=m.phase, fen_before=m.fen_before, eval_change=m.eval_change, classification=m.classification, best_move=m.best_move, note=m.note)
def _is_player_move(player_colour, move): return player_colour is None or move.side == player_colour
def _critical_moments_for_player(gid, moves, player_colour): return [_critical(gid,m) for m in moves if m.classification in CRITICAL_CLASSIFICATIONS and _is_player_move(player_colour, m)]
def analyse_game(parsed:ParsedGame, config:ChessCoachConfig, mock:bool=False):
    ok,path=stockfish_available(config)
    if (not ok) or mock: return analyse_game_mock(parsed,path)
    try: return analyse_game_stockfish(parsed,config,path or 'stockfish')
    except Exception as e:
        a=analyse_game_mock(parsed,path); a.warnings.append(f'Stockfish analysis failed; mock heuristics used instead: {e}'); return a
def analyse_game_mock(parsed, stockfish_hint=None):
    warnings=['Stockfish unavailable; generated mock heuristic analysis. Set STOCKFISH_PATH or install stockfish for engine evaluations.']
    if stockfish_hint: warnings.append(f'Configured Stockfish candidate was not usable: {stockfish_hint}')
    board=chess.Board(); moves=[]
    for pm in parsed.moves:
        fen_before=board.fen()
        if '??' in pm.san: ch,ec,n='blunder',-2.2,'Heuristic: PGN annotation marks this as a severe error.'
        elif '?' in pm.san: ch,ec,n='mistake',-1.1,'Heuristic: PGN annotation marks this as a mistake.'
        elif '!' in pm.san: ch,ec,n='book/neutral',0.2,'Heuristic: PGN annotation suggests an acceptable move.'
        else: ch,ec,n='book/neutral',0.0,'No engine available; move not classified beyond neutral heuristic.'
        moves.append(MoveAnalysis(move_number=pm.move_number, side=pm.side, san=pm.san, uci=pm.uci, phase=phase_for_move(pm.move_number), fen_before=fen_before, eval_change=ec, classification=ch, note=n))
        board.push(chess.Move.from_uci(pm.uci))
    crit=_critical_moments_for_player(parsed.game_id,moves,parsed.player_colour)
    return GameAnalysis(game_id=parsed.game_id,event=parsed.event,site=parsed.site,date=parsed.date,white=parsed.white,black=parsed.black,result=parsed.result,player_colour=parsed.player_colour,headers=parsed.headers,moves=moves,critical_moments=crit,analysis_engine='mock',stockfish_available=False,warnings=warnings)
def _score(score, turn):
    pov=score.pov(turn); mate=pov.mate()
    if mate is not None: return 100.0 if mate>0 else -100.0
    return (pov.score(mate_score=10000) or 0)/100.0
def analyse_game_stockfish(parsed, config, engine_path):
    board=chess.Board(); moves=[]; limit=chess.engine.Limit(depth=config.stockfish_depth,time=config.stockfish_time_limit)
    with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
        for pm in parsed.moves:
            turn=board.turn; fen_before=board.fen(); before=engine.analyse(board,limit); eb=_score(before['score'],turn); pv=before.get('pv') or []; best=pv[0].uci() if pv else None
            board.push(chess.Move.from_uci(pm.uci)); after=engine.analyse(board,limit); ea=_score(after['score'],turn); change=ea-eb; cls=classify_eval_loss(max(0,-change),pm.san)
            moves.append(MoveAnalysis(move_number=pm.move_number, side=pm.side, san=pm.san, uci=pm.uci, phase=phase_for_move(pm.move_number), fen_before=fen_before, eval_before=round(eb,2), eval_after=round(ea,2), eval_change=round(change,2), best_move=best, classification=cls))
    crit=_critical_moments_for_player(parsed.game_id,moves,parsed.player_colour)
    return GameAnalysis(game_id=parsed.game_id,event=parsed.event,site=parsed.site,date=parsed.date,white=parsed.white,black=parsed.black,result=parsed.result,player_colour=parsed.player_colour,headers=parsed.headers,moves=moves,critical_moments=crit,analysis_engine='stockfish',stockfish_available=True)
