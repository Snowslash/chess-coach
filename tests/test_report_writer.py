from chess_coach.models import AnalysisBundle, CriticalMoment, GameAnalysis, MoveAnalysis, PatternSummary
from chess_coach.report_writer import render_markdown


def test_render_markdown_includes_fen_for_critical_positions():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    bundle = AnalysisBundle(
        source_pgn="input/game.pgn",
        games=[
            GameAnalysis(
                game_id="g1",
                event="Training",
                date="2026.05.30",
                moves=[
                    MoveAnalysis(
                        move_number=1,
                        side="white",
                        san="e4??",
                        uci="e2e4",
                        phase="opening",
                        fen_before=fen,
                        eval_change=-2.4,
                        classification="blunder",
                        best_move="g1f3",
                    )
                ],
                critical_moments=[
                    CriticalMoment(
                        game_id="g1",
                        move_number=1,
                        side="white",
                        san="e4??",
                        phase="opening",
                        fen_before=fen,
                        eval_change=-2.4,
                        classification="blunder",
                        best_move="g1f3",
                    )
                ],
            )
        ],
        patterns=PatternSummary(games_analysed=1, critical_moments=1, training_priorities=["Reduce blunders."]),
    )

    markdown = render_markdown(bundle, "reports/game.json", "reports/game.md")

    assert f"FEN: `{fen}`" in markdown
    assert "Top priority: Reduce blunders." in markdown
    assert ".." not in markdown.split("## Recurring weaknesses", 1)[0]


def test_render_markdown_most_important_mistakes_only_uses_player_colour():
    bundle = AnalysisBundle(
        source_pgn="input/game.pgn",
        games=[
            GameAnalysis(
                game_id="g1",
                event="Training",
                date="2026.05.30",
                player_colour="white",
                moves=[
                    MoveAnalysis(move_number=1, side="white", san="e4?", uci="e2e4", phase="opening", eval_change=-1.2, classification="mistake"),
                    MoveAnalysis(move_number=1, side="black", san="e5??", uci="e7e5", phase="opening", eval_change=-9.0, classification="blunder"),
                ],
            )
        ],
        patterns=PatternSummary(games_analysed=1, critical_moments=1, training_priorities=["Review own mistakes."]),
    )

    markdown = render_markdown(bundle, "reports/game.json", "reports/game.md")

    most_important = markdown.split("## Most important mistakes", 1)[1].split("## Opening notes", 1)[0]
    assert "e4?" in most_important
    assert "e5??" not in most_important


def test_render_markdown_includes_maia2_human_likeness_section():
    bundle = AnalysisBundle(
        source_pgn="input/game.pgn",
        games=[
            GameAnalysis(
                game_id="g1",
                event="Training",
                date="2026.05.30",
                player_colour="white",
                moves=[
                    MoveAnalysis(
                        move_number=12,
                        side="white",
                        san="Nxe5?",
                        uci="f3e5",
                        phase="middlegame",
                        classification="mistake",
                        eval_change=-1.3,
                        maia2_played_move_prob=0.08,
                        maia2_top_moves={"d2d4": 0.31, "f3e5": 0.08},
                        maia2_win_prob=0.42,
                    )
                ],
            )
        ],
        patterns=PatternSummary(games_analysed=1, critical_moments=1),
        metadata={"maia2_enabled": True, "maia2_available": True, "maia2_target_elo": 1500},
    )

    markdown = render_markdown(bundle, "reports/game.json", "reports/game.md")

    human_section = markdown.split("## Maia 2 human-likeness", 1)[1].split("## Critical positions", 1)[0]
    assert "target Elo 1500" in human_section
    assert "move 12 white `Nxe5?`" in human_section
    assert "played 8.0%" in human_section
    assert "top Maia 2 `d2d4` 31.0%" in human_section
    assert "win probability 42.0%" in human_section
    assert "not yet wired" not in markdown
    assert "Maia 2 human-likeness scoring is available" in markdown


def test_render_markdown_summarises_maia2_instead_of_dumping_every_move():
    bundle = AnalysisBundle(
        source_pgn="input/game.pgn",
        games=[
            GameAnalysis(
                game_id="g1",
                event="Training",
                date="2026.05.30",
                player_colour="white",
                moves=[
                    MoveAnalysis(
                        move_number=1,
                        side="white",
                        san="Nf3",
                        uci="g1f3",
                        phase="opening",
                        classification="book/neutral",
                        eval_change=-0.1,
                        maia2_played_move_prob=0.5,
                        maia2_top_moves={"g1f3": 0.5},
                        maia2_win_prob=0.51,
                    ),
                    MoveAnalysis(
                        move_number=2,
                        side="white",
                        san="Qh5??",
                        uci="d1h5",
                        phase="opening",
                        classification="blunder",
                        eval_change=-3.0,
                        best_move="d2d4",
                        maia2_played_move_prob=0.01,
                        maia2_top_moves={"d2d4": 0.4, "d1h5": 0.01},
                        maia2_win_prob=0.2,
                    ),
                    MoveAnalysis(
                        move_number=3,
                        side="white",
                        san="Bxf7?",
                        uci="c4f7",
                        phase="middlegame",
                        classification="blunder",
                        eval_change=-2.5,
                        best_move="e1g1",
                        maia2_played_move_prob=0.72,
                        maia2_top_moves={"c4f7": 0.72, "e1g1": 0.12},
                        maia2_win_prob=0.31,
                    ),
                    MoveAnalysis(
                        move_number=3,
                        side="black",
                        san="Nc6",
                        uci="b8c6",
                        phase="opening",
                        classification="book/neutral",
                        maia2_played_move_prob=0.8,
                    ),
                ],
            )
        ],
        patterns=PatternSummary(games_analysed=1, critical_moments=2),
        metadata={"maia2_enabled": True, "maia2_available": True, "maia2_target_elo": 1500},
    )

    markdown = render_markdown(bundle, "reports/game.json", "reports/game.md")

    human_section = markdown.split("## Maia 2 human-likeness", 1)[1].split("## Critical positions", 1)[0]
    assert "Player moves scored: 3/3" in human_section
    assert "mean played-move probability 41.0%" in human_section
    assert "median 50.0%" in human_section
    assert "under 5%: 1" in human_section
    assert "### Bad + Maia-unlikely moves" in human_section
    assert "Qh5??" in human_section
    assert "played 1.0%" in human_section
    assert "### Bad but Maia-human-likely moves" in human_section
    assert "Bxf7?" in human_section
    assert "played 72.0%" in human_section
    assert "Full per-move Maia data is in `reports/game.json`." in human_section
    assert "move 1 white `Nf3`" not in human_section
    assert "move 3 black `Nc6`" not in human_section


def test_maia2_opening_observations_do_not_promote_book_neutral_noise():
    bundle = AnalysisBundle(
        source_pgn="input/game.pgn",
        games=[
            GameAnalysis(
                game_id="g1",
                event="Training",
                date="2026.05.30",
                player_colour="white",
                moves=[
                    MoveAnalysis(
                        move_number=1,
                        side="white",
                        san="c4",
                        uci="c2c4",
                        phase="opening",
                        classification="book/neutral",
                        eval_change=-0.3,
                        maia2_played_move_prob=0.01,
                        maia2_top_moves={"g1f3": 0.32},
                    ),
                    MoveAnalysis(
                        move_number=4,
                        side="white",
                        san="e3?!",
                        uci="e2e3",
                        phase="opening",
                        classification="inaccuracy",
                        eval_change=-0.9,
                        best_move="f1g2",
                        maia2_played_move_prob=0.04,
                        maia2_top_moves={"f1g2": 0.83},
                    ),
                ],
            )
        ],
        patterns=PatternSummary(games_analysed=1, critical_moments=1),
        metadata={"maia2_enabled": True, "maia2_available": True, "maia2_target_elo": 1500},
    )

    markdown = render_markdown(bundle, "reports/game.json", "reports/game.md")

    human_section = markdown.split("## Maia 2 human-likeness", 1)[1].split("## Critical positions", 1)[0]
    opening_section = human_section.split("### Opening repertoire/style observations", 1)[1]
    assert "e3?!" in opening_section
    assert "c4" not in opening_section
