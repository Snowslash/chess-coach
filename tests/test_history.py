from chess_coach.models import AnalysisBundle, CriticalMoment, GameAnalysis, MoveAnalysis, PatternSummary


def make_game(game_id: str = "abc", site: str = "https://lichess.org/abc") -> GameAnalysis:
    return GameAnalysis(
        game_id=game_id,
        site=site,
        date="2026.06.04",
        white="TestPlayer",
        black="Opponent",
        result="1-0",
        player_colour="white",
        moves=[
            MoveAnalysis(move_number=10, side="white", san="Qh5", uci="d1h5", phase="middlegame", classification="blunder"),
            MoveAnalysis(move_number=10, side="black", san="Nf6", uci="g8f6", phase="middlegame", classification="book/neutral"),
            MoveAnalysis(move_number=20, side="white", san="Re1", uci="f1e1", phase="endgame", classification="mistake"),
        ],
        critical_moments=[
            CriticalMoment(
                game_id=game_id,
                move_number=10,
                side="white",
                san="Qh5",
                phase="middlegame",
                fen_before="fen-1",
                eval_change=2.4,
                classification="blunder",
                best_move="Nf6",
                note="Dropped a tactic.",
            ),
            CriticalMoment(
                game_id=game_id,
                move_number=20,
                side="black",
                san="Re1",
                phase="middlegame",
                fen_before="fen-2",
                eval_change=1.1,
                classification="mistake",
                best_move="Qe2",
                note="Missed a simplification.",
            ),
        ],
    )


def make_bundle(games: list[GameAnalysis]) -> AnalysisBundle:
    return AnalysisBundle(
        source_pgn="input/sample_games.pgn",
        games=games,
        patterns=PatternSummary(
            games_analysed=len(games),
            critical_moments=sum(len(game.critical_moments) for game in games),
            recurring_weaknesses=["Middlegame tactics"],
            training_priorities=["Review middlegame tactical misses"],
        ),
    )


def test_empty_coach_state_has_schema_version_and_no_games():
    from chess_coach.history import CoachState

    state = CoachState()

    assert state.schema_version == 1
    assert state.games == {}
    assert state.patterns == {}
    assert state.runs == []


def test_game_history_key_is_stable_from_game_identity():
    from chess_coach.history import game_history_key

    game = GameAnalysis(
        game_id="abc",
        site="https://lichess.org/abc",
        date="2026.06.04",
        white="TestPlayer",
        black="Opponent",
        result="1-0",
    )

    assert game_history_key(game) == "lichess:abc"


def test_game_history_key_falls_back_to_headers_when_site_is_not_lichess():
    from chess_coach.history import game_history_key

    game = GameAnalysis(
        game_id="sample-1",
        site="https://example.com/game/1",
        date="2026.06.04",
        white="TestPlayer",
        black="Opponent",
        result="1-0",
        headers={"Site": "https://example.com/game/1"},
    )

    assert game_history_key(game).startswith("pgn:")


def test_load_state_returns_empty_state_when_file_missing(tmp_path):
    from chess_coach.history import CoachState, load_state

    state = load_state(tmp_path / ".coach" / "state.json")

    assert isinstance(state, CoachState)
    assert state.games == {}


def test_save_state_creates_parent_and_round_trips(tmp_path):
    from chess_coach.history import CoachState, GameHistoryEntry, load_state, save_state

    path = tmp_path / ".coach" / "state.json"
    state = CoachState(games={"x": GameHistoryEntry(key="x", game_id="x")})

    save_state(state, path)
    loaded = load_state(path)

    assert loaded.games["x"].game_id == "x"


def test_history_entry_from_game_counts_signals():
    from chess_coach.history import history_entry_from_game

    entry = history_entry_from_game(make_game())

    assert entry.critical_moments == 2
    assert entry.classification_counts["blunder"] == 1
    assert entry.classification_counts["mistake"] == 1
    assert entry.phase_counts["middlegame"] == 2
    assert entry.side_counts["white"] == 1
    assert entry.side_counts["black"] == 1
    assert entry.opening_family == "Qh5 Nf6 Re1"


def test_update_state_from_bundle_adds_games_and_run():
    from chess_coach.history import CoachState, update_state_from_bundle

    bundle = make_bundle([make_game("abc"), make_game("def", "https://lichess.org/def")])

    updated = update_state_from_bundle(CoachState(), bundle)

    assert len(updated.games) == 2
    assert len(updated.runs) == 1
    assert updated.runs[0].games_analysed == 2
    assert updated.runs[0].critical_moments == 4
    assert updated.runs[0].top_patterns == ["Review middlegame tactical misses"]


def test_update_state_from_bundle_deduplicates_existing_games():
    from chess_coach.history import CoachState, update_state_from_bundle

    bundle = make_bundle([make_game("abc"), make_game("def", "https://lichess.org/def")])

    once = update_state_from_bundle(CoachState(), bundle)
    twice = update_state_from_bundle(once, bundle)

    assert len(twice.games) == len(once.games)
    assert len(twice.runs) == 2



def test_filter_new_games_excludes_games_already_in_state():
    from chess_coach.history import CoachState, filter_new_games, game_history_key, history_entry_from_game

    old_game = make_game("abc")
    new_game = make_game("new", "https://lichess.org/new")
    state = CoachState(games={game_history_key(old_game): history_entry_from_game(old_game)})

    filtered = filter_new_games([old_game, new_game], state)

    assert [game.game_id for game in filtered] == ["new"]
    assert list(state.games) == [game_history_key(old_game)]
