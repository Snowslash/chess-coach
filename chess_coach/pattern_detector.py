from __future__ import annotations
from collections import Counter
from .models import GameAnalysis, MoveAnalysis, PatternSummary
IMPORTANT={"inaccuracy","mistake","blunder","missed win","tactical miss"}
def _is_player_move(game:GameAnalysis, move:MoveAnalysis)->bool: return game.player_colour is None or move.side == game.player_colour
def _important_moves(games:list[GameAnalysis])->list[MoveAnalysis]: return [m for g in games for m in g.moves if m.classification in IMPORTANT and _is_player_move(g,m)]
def _top(counter:Counter, fallback:str)->str: return counter.most_common(1)[0][0] if counter else fallback
def _training_plan(top_priorities:list[str], phase_counts:Counter, side_counts:Counter, class_counts:Counter)->list[str]:
    main=top_priorities[0] if top_priorities else 'Review the critical positions from this report.'
    phase=_top(phase_counts,'critical-moment')
    side=_top(side_counts,'your colour')
    side_label = f'{side} games' if side in {'white','black'} else 'games from your colour'
    side_position = side if side in {'white','black'} else 'your colour'
    cls=_top(class_counts,'mistake')
    if phase == 'opening': phase_task='rebuild the first 10 moves of each affected game and write the first avoidable concession.'
    elif phase == 'middlegame': phase_task='replay each middlegame critical position and list three candidate moves before checking the engine.'
    elif phase == 'endgame': phase_task='set up the endgame critical positions and practise the conversion/defence technique against engine resistance.'
    else: phase_task='replay the highest eval-swing positions without engine help, then compare.'
    if cls == 'blunder': class_task='run a strict checks-captures-threats blunder scan before every move in two slow games.'
    elif cls == 'mistake': class_task='for each mistake, write the missed plan or tactical resource in one sentence.'
    elif cls == 'inaccuracy': class_task='compare your move with the engine move and write what small positional concession changed.'
    elif cls == 'missed win': class_task='drill forcing continuations from the missed-win positions until the winning idea is automatic.'
    elif cls == 'tactical miss': class_task='do short tactics sets filtered for forcing moves, pins, forks and loose pieces.'
    else: class_task='review one recurring error type from the report.'
    return [
        f'Day 1: Review the top critical positions. Main focus: {main}',
        f'Day 2: {phase.title()} repair — {phase_task}',
        f'Day 3: Colour-specific review — study the {side_label} and identify the earliest repeatable decision point.',
        f'Day 4: Error-type drill — {class_task}',
        'Day 5: Replay the 5 largest eval swings without engine help; choose 3 candidate moves before revealing the best move.',
        f'Day 6: Play 2 slower games using the report checklist, with extra care in {phase} positions as {side_position}.',
        'Day 7: Reanalyse fresh PGNs and keep only one highest-yield priority for the next week.',
    ]
def detect_patterns(games:list[GameAnalysis])->PatternSummary:
    crit=_important_moves(games); cc=Counter(m.classification for m in crit); pc=Counter(m.phase for m in crit); sc=Counter(m.side for m in crit); recurring=[]
    for cls,c in cc.most_common(): recurring.append(f'{cls.title()} appears {c} time(s) in critical moments.')
    for ph,c in pc.most_common(): recurring.append(f'Repeated {ph} errors ({c}). Heuristic: review this phase.')
    if cc.get('tactical miss',0) or cc.get('blunder',0)>=2: recurring.append('Tactical misses/blunders are prominent. Heuristic: train forcing-move checks, captures and threats before strategy work.')
    if sc:
        side,c=sc.most_common(1)[0]; recurring.append(f'Most critical moments occurred as {side} ({c}). Treat colour-specific opening and plan selection as a review target.')
    opening=[x for x in recurring if 'opening' in x.lower()]; mid=[x for x in recurring if 'middlegame' in x.lower() or 'tactical' in x.lower()]; end=[x for x in recurring if 'endgame' in x.lower()]
    pri=[]
    if cc.get('blunder',0): pri.append('Blunder reduction: pause before each move and inspect checks, captures and threats for both sides.')
    if cc.get('tactical miss',0) or cc.get('mistake',0): pri.append('Tactical pattern work: short daily sets focused on one-move and two-move tactics, then review missed motifs.')
    if pc.get('opening',0): pri.append('Opening discipline: review the first 10 moves of losses and identify the first avoidable concession.')
    if pc.get('endgame',0): pri.append('Endgame technique: practise basic conversion/defensive themes from critical positions.')
    if not pri: pri.append('Collect more analysed games or run Stockfish; current data shows no recurring engine-backed weakness.')
    top=pri[:3]
    plan=_training_plan(top,pc,sc,cc)
    uncertainty=['Pattern detection is heuristic and based on eval swings/classifications, not deep semantic position understanding.']
    if any(not g.stockfish_available for g in games): uncertainty.append('At least one game used mock analysis because Stockfish was unavailable; treat chess conclusions as pipeline smoke-test output only.')
    return PatternSummary(games_analysed=len(games),critical_moments=len(crit),classification_counts=dict(cc),phase_counts=dict(pc),side_counts=dict(sc),recurring_weaknesses=recurring or ['No repeated critical-moment pattern detected from the available data.'],opening_notes=opening or ['No specific opening pattern detected from available critical moments.'],middlegame_notes=mid or ['No specific middlegame pattern detected from available critical moments.'],endgame_notes=end or ['No specific endgame pattern detected from available critical moments.'],training_priorities=top,training_plan_7_days=plan,uncertainty_notes=uncertainty)
