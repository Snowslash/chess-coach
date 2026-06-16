from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .flashcards import ReviewCard
from .models import AnalysisBundle


class TrainingTask(BaseModel):
    task_id: str
    text: str
    linked_pattern: str | None = None
    linked_card_ids: list[str] = Field(default_factory=list)
    measure: str
    verification: str
    timebox: str
    success_metric: str


class TrainingPlan(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    tasks: list[TrainingTask] = Field(default_factory=list)
    uncertainty_notes: list[str] = Field(default_factory=list)


def build_training_plan(bundle: AnalysisBundle, cards: list[ReviewCard]) -> TrainingPlan:
    tasks: list[TrainingTask] = []
    uncertainty_notes: list[str] = []
    top_priority = (bundle.patterns.training_priorities or bundle.patterns.recurring_weaknesses or ["Review the highest-yield theme from the latest report"])[0]

    if cards:
        primary_theme = cards[0].theme
        linked_card_ids = [card.card_id for card in cards[: min(3, len(cards))]]
        tasks.append(
            TrainingTask(
                task_id="task-1",
                text=f"Review {len(linked_card_ids)} card-backed position(s) tagged {primary_theme} and say the best move before revealing it.",
                linked_pattern=top_priority,
                linked_card_ids=linked_card_ids,
                measure=f"Complete {len(linked_card_ids)} position reviews with a written candidate move for each.",
                verification="Check each reviewed card against the engine best move and explanation after committing to your candidate move.",
                timebox=f"{5 * len(linked_card_ids)} position reps",
                success_metric="Name the best move or plan correctly on at least two thirds of the reviewed positions.",
            )
        )

    if not cards:
        tasks.append(
            TrainingTask(
                task_id="task-1",
                text=f"Review the top training priority from the report: {top_priority}.",
                linked_pattern=top_priority,
                linked_card_ids=[],
                measure="Write one concrete pre-move checklist item you will apply in the next analysed session.",
                verification="Reanalyse a fresh game batch and check whether the same priority remains at the top.",
                timebox="1 annotated review pass",
                success_metric="The same priority should appear less often or drop below the top slot in the next report.",
            )
        )
        uncertainty_notes.append("No review cards were available, so the plan falls back to report priorities and recurring weaknesses.")

    if bundle.patterns.recurring_weaknesses:
        weakness = bundle.patterns.recurring_weaknesses[0]
        tasks.append(
            TrainingTask(
                task_id=f"task-{len(tasks) + 1}",
                text=f"Run a focused repair block for {weakness} using the latest critical moments and one fresh slow game.",
                linked_pattern=weakness,
                linked_card_ids=[],
                measure="Annotate one repeatable cue and one safer alternative plan before the next analysed game.",
                verification="In the next analysis batch, compare whether this theme appears fewer times than it did in the current report.",
                timebox="1 slow game plus post-game annotation",
                success_metric="Next analysis should show fewer critical moments linked to this theme than the current batch.",
            )
        )

    return TrainingPlan(generated_at=bundle.generated_at, tasks=tasks, uncertainty_notes=uncertainty_notes)


def write_training_plan_markdown(plan: TrainingPlan, out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Chess Coach Training Plan", "", f"Generated: {plan.generated_at.strftime('%Y-%m-%d %H:%M')}", ""]
    if not plan.tasks:
        lines.extend(["No training tasks were generated.", ""])
    for index, task in enumerate(plan.tasks, start=1):
        lines.extend(
            [
                f"## Task {index} — {task.task_id}",
                "",
                task.text,
                "",
                f"- Linked pattern: {task.linked_pattern or 'None'}",
                f"- Linked cards: {', '.join(task.linked_card_ids) if task.linked_card_ids else 'None'}",
                f"- Timebox: {task.timebox}",
                f"- Measure: {task.measure}",
                f"- Verification: {task.verification}",
                f"- Success metric: {task.success_metric}",
                "",
            ]
        )
    lines.extend(["## Uncertainty", ""])
    if plan.uncertainty_notes:
        lines.extend(f"- {note}" for note in plan.uncertainty_notes)
    else:
        lines.append("- None.")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path
