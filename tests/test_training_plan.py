from datetime import datetime

from chess_coach.flashcards import cards_from_bundle
from chess_coach.models import AnalysisBundle, CriticalMoment, GameAnalysis, PatternSummary



def make_bundle() -> AnalysisBundle:
    return AnalysisBundle(
        generated_at=datetime(2026, 6, 4, 12, 0, 0),
        source_pgn="input/sample_games.pgn",
        games=[
            GameAnalysis(
                game_id="abc",
                site="https://lichess.org/abc",
                date="2026.06.04",
                white="TestPlayer",
                black="Opponent",
                result="1-0",
                player_colour="white",
                critical_moments=[
                    CriticalMoment(
                        game_id="abc",
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
                        game_id="abc",
                        move_number=22,
                        side="white",
                        san="Re1",
                        phase="endgame",
                        fen_before="fen-2",
                        eval_change=1.1,
                        classification="mistake",
                        best_move="Qe2",
                        note="Missed a simplification.",
                    ),
                ],
            )
        ],
        patterns=PatternSummary(
            games_analysed=1,
            critical_moments=2,
            recurring_weaknesses=["Middlegame tactics", "Endgame conversion"],
            training_priorities=["Review middlegame tactical misses", "Convert cleaner endgames"],
        ),
    )



def test_training_plan_uses_cards_and_patterns_not_generic_advice():
    from chess_coach.training_plan import build_training_plan

    bundle = make_bundle()
    cards = cards_from_bundle(bundle)

    plan = build_training_plan(bundle, cards)
    text = "\n".join(task.text for task in plan.tasks)

    assert "review" in text.lower()
    assert "card" in text.lower() or "position" in text.lower()
    assert "10 minutes" not in text.lower()
    assert any(task.linked_card_ids for task in plan.tasks)



def test_training_task_has_measure_and_verification():
    from chess_coach.training_plan import build_training_plan

    bundle = make_bundle()
    cards = cards_from_bundle(bundle)

    task = build_training_plan(bundle, cards).tasks[0]
    assert task.measure
    assert task.verification
    assert task.linked_card_ids or task.linked_pattern
    assert task.success_metric
    assert task.timebox



def test_training_plan_falls_back_to_priorities_when_no_cards():
    from chess_coach.training_plan import build_training_plan

    bundle = make_bundle()
    bundle.games[0].critical_moments[0].fen_before = None
    bundle.games[0].critical_moments[1].fen_before = None

    plan = build_training_plan(bundle, cards=[])

    assert plan.tasks
    assert plan.tasks[0].linked_pattern == "Review middlegame tactical misses"
    assert "No review cards were available" in plan.uncertainty_notes[0]



def test_write_training_plan_markdown_contains_measures(tmp_path):
    from chess_coach.training_plan import build_training_plan, write_training_plan_markdown

    bundle = make_bundle()
    cards = cards_from_bundle(bundle)
    plan = build_training_plan(bundle, cards)
    out_path = tmp_path / "training_plan.md"

    write_training_plan_markdown(plan, out_path)
    text = out_path.read_text(encoding="utf-8")

    assert "# Chess Coach Training Plan" in text
    assert "Measure:" in text
    assert "Verification:" in text
    assert "Success metric:" in text
