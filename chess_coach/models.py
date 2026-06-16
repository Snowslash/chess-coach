from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field
Classification = Literal["book/neutral","inaccuracy","mistake","blunder","missed win","tactical miss"]
Phase = Literal["opening","middlegame","endgame"]
Side = Literal["white","black"]
class ParsedMove(BaseModel):
    move_number:int; side:Side; san:str; uci:str
class ParsedGame(BaseModel):
    game_id:str; event:str="?"; site:str="?"; date:str="?"; white:str="?"; black:str="?"; result:str="*"; player_colour:Side|None=None; headers:dict[str,str]=Field(default_factory=dict); moves:list[ParsedMove]=Field(default_factory=list)
class MoveAnalysis(BaseModel):
    move_number:int; side:Side; san:str; uci:str; phase:Phase; fen_before:str|None=None; eval_before:float|None=None; eval_after:float|None=None; eval_change:float|None=None; best_move:str|None=None; classification:Classification="book/neutral"; note:str|None=None; maia2_played_move_prob:float|None=None; maia2_top_moves:dict[str,float]=Field(default_factory=dict); maia2_win_prob:float|None=None
class CriticalMoment(BaseModel):
    game_id:str; move_number:int; side:Side; san:str; phase:Phase; fen_before:str|None=None; eval_change:float|None; classification:Classification; best_move:str|None=None; note:str|None=None
class GameAnalysis(BaseModel):
    game_id:str; event:str="?"; site:str="?"; date:str="?"; white:str="?"; black:str="?"; result:str="*"; player_colour:Side|None=None; headers:dict[str,str]=Field(default_factory=dict); moves:list[MoveAnalysis]=Field(default_factory=list); critical_moments:list[CriticalMoment]=Field(default_factory=list); analysis_engine:str="mock"; stockfish_available:bool=False; warnings:list[str]=Field(default_factory=list)
class PatternSummary(BaseModel):
    games_analysed:int; critical_moments:int; classification_counts:dict[str,int]=Field(default_factory=dict); phase_counts:dict[str,int]=Field(default_factory=dict); side_counts:dict[str,int]=Field(default_factory=dict); recurring_weaknesses:list[str]=Field(default_factory=list); opening_notes:list[str]=Field(default_factory=list); middlegame_notes:list[str]=Field(default_factory=list); endgame_notes:list[str]=Field(default_factory=list); training_priorities:list[str]=Field(default_factory=list); training_plan_7_days:list[str]=Field(default_factory=list); uncertainty_notes:list[str]=Field(default_factory=list)
class AnalysisBundle(BaseModel):
    generated_at:datetime=Field(default_factory=datetime.now); source_pgn:str; games:list[GameAnalysis]; patterns:PatternSummary; metadata:dict[str,Any]=Field(default_factory=dict)
class CoachReport(BaseModel):
    markdown:str; json_path:str; markdown_path:str
