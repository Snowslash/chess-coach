from chess_coach.models import GameAnalysis, MoveAnalysis



def game_with_moves(sans: list[str]) -> GameAnalysis:
    moves = [
        MoveAnalysis(
            move_number=(index // 2) + 1,
            side="white" if index % 2 == 0 else "black",
            san=san,
            uci=f"move{index}",
            phase="opening",
        )
        for index, san in enumerate(sans)
    ]
    return GameAnalysis(game_id="g1", moves=moves)



def test_opening_family_uses_first_few_san_moves():
    from chess_coach.openings import opening_family_from_game

    family = opening_family_from_game(game_with_moves(["e4", "e5", "Nf3", "Nc6", "Bc4"]))

    assert family == "e4 e5 Nf3 Nc6 Bc4"



def test_opening_family_returns_none_for_empty_games():
    from chess_coach.openings import opening_family_from_game

    assert opening_family_from_game(game_with_moves([])) is None



def test_opening_family_ignores_missing_san_and_respects_plies():
    from chess_coach.openings import opening_family_from_game

    game = game_with_moves(["e4", "", "Nf3", "Nc6", "Bb5", "a6"])

    assert opening_family_from_game(game, plies=4) == "e4 Nf3 Nc6"
