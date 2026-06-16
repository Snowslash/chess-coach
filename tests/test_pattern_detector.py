from chess_coach.models import GameAnalysis, MoveAnalysis
from chess_coach.pattern_detector import detect_patterns
def move(move_number, side, classification, eval_change=-1.2, phase='middlegame', san='??'):
    return MoveAnalysis(move_number=move_number,side=side,san=san,uci='e2e4',phase=phase,eval_before=0.3,eval_after=eval_change,eval_change=eval_change,best_move='e2e4',classification=classification)
def test_detect_patterns_finds_phase_and_colour_weaknesses():
    games=[GameAnalysis(game_id='g1',event='Game 1',date='2026.05.30',white='TestPlayer',black='A',result='0-1',player_colour='white',moves=[move(7,'white','blunder',-2.5,'opening'),move(23,'white','mistake',-1.2,'middlegame')]),GameAnalysis(game_id='g2',event='Game 2',date='2026.05.30',white='B',black='TestPlayer',result='1-0',player_colour='black',moves=[move(8,'black','blunder',-2.2,'opening'),move(31,'black','tactical miss',-1.4,'endgame')])]
    s=detect_patterns(games); assert s.games_analysed==2; assert s.critical_moments==4; assert s.classification_counts['blunder']==2; assert any('opening' in x.lower() for x in s.recurring_weaknesses); assert any('tactical' in x.lower() for x in s.recurring_weaknesses); assert s.training_priorities[0]; assert len(s.training_plan_7_days)==7


def test_detect_patterns_ignores_opponent_mistakes_when_player_colour_known():
    games=[GameAnalysis(game_id='g1',player_colour='white',moves=[move(1,'white','mistake',-1.2,'opening'),move(1,'black','blunder',-4.0,'opening')])]
    s=detect_patterns(games)
    assert s.critical_moments==1
    assert s.classification_counts=={'mistake': 1}
    assert s.side_counts=={'white': 1}


def test_training_plan_uses_report_specific_weakest_phase_and_colour():
    opening_white_games=[GameAnalysis(game_id='g1',player_colour='white',moves=[
        move(3,'white','mistake',-1.0,'opening','Nc3'),
        move(6,'white','inaccuracy',-0.7,'opening','e3'),
    ])]
    endgame_black_games=[GameAnalysis(game_id='g2',player_colour='black',moves=[
        move(42,'black','blunder',-3.0,'endgame','Kf8'),
        move(48,'black','mistake',-1.5,'endgame','h5'),
    ])]

    opening_plan=detect_patterns(opening_white_games).training_plan_7_days
    endgame_plan=detect_patterns(endgame_black_games).training_plan_7_days

    assert opening_plan != endgame_plan
    assert any('opening' in item.lower() for item in opening_plan)
    assert any('white' in item.lower() for item in opening_plan)
    assert any('endgame' in item.lower() for item in endgame_plan)
    assert any('black' in item.lower() for item in endgame_plan)


def test_training_plan_has_clean_fallback_when_no_critical_moments():
    plan=detect_patterns([GameAnalysis(game_id='quiet',moves=[])]).training_plan_7_days
    rendered='\n'.join(plan).lower()
    assert 'your games' not in rendered
    assert 'as your.' not in rendered
    assert 'your colour' in rendered
