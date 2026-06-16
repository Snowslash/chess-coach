from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from .history import CoachState


def _bullets(items: list[str], empty: str) -> list[str]:
    return [f"- {item}" for item in items] if items else [f"- {empty}"]


class WeeklyReview(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    games_analysed: int = 0
    total_known_games: int = 0
    critical_moments: int = 0
    top_patterns: list[str] = Field(default_factory=list)
    opening_notes: list[str] = Field(default_factory=list)
    improved: list[str] = Field(default_factory=list)
    worsened: list[str] = Field(default_factory=list)
    stable: list[str] = Field(default_factory=list)
    latest_critical_moments_per_game: float | None = None
    previous_critical_moments_per_game: float | None = None
    aggregate_trend: Literal["improving", "worsening", "stable", "unknown"] = "unknown"
    aggregate_trend_note: str | None = None
    uncertainty_notes: list[str] = Field(default_factory=list)


def build_weekly_review(state: CoachState) -> WeeklyReview:
    review = WeeklyReview(total_known_games=len(state.games))
    if not state.runs:
        review.uncertainty_notes.append("No coach history is available yet. Run analyse --update-state before generating a weekly review.")
        return review

    latest_run = state.runs[-1]
    review.games_analysed = latest_run.games_analysed
    review.critical_moments = latest_run.critical_moments
    review.top_patterns = list(latest_run.top_patterns)

    for pattern in sorted(state.patterns.values(), key=lambda item: (-item.occurrences, item.label)):
        if pattern.trend == "improving":
            review.improved.append(pattern.label)
        elif pattern.trend == "worsening":
            review.worsened.append(pattern.label)
        elif pattern.trend == "stable":
            review.stable.append(pattern.label)

    opening_totals: dict[str, tuple[int, int]] = {}
    for entry in state.games.values():
        if not entry.opening_family:
            continue
        total_critical, total_games = opening_totals.get(entry.opening_family, (0, 0))
        opening_totals[entry.opening_family] = (total_critical + entry.critical_moments, total_games + 1)
    review.opening_notes = [
        f"{family}: {critical} critical moments across {games} {'game' if games == 1 else 'games'}"
        for family, (critical, games) in sorted(opening_totals.items(), key=lambda item: (-item[1][0], -item[1][1], item[0]))
    ]

    if len(state.runs) < 2:
        review.uncertainty_notes.append("Trend needs at least two runs before week-over-week changes are meaningful.")
        return review

    previous_run = state.runs[-2]
    if previous_run.games_analysed <= 0 or latest_run.games_analysed <= 0:
        review.aggregate_trend = "unknown"
        review.aggregate_trend_note = (
            "Cannot compare critical moments per game because the previous or latest run analysed zero games."
        )
        review.uncertainty_notes.append(review.aggregate_trend_note)
        return review

    review.previous_critical_moments_per_game = previous_run.critical_moments / previous_run.games_analysed
    review.latest_critical_moments_per_game = latest_run.critical_moments / latest_run.games_analysed

    previous_rate = review.previous_critical_moments_per_game
    latest_rate = review.latest_critical_moments_per_game

    if latest_rate < previous_rate:
        review.aggregate_trend = "improving"
    elif latest_rate > previous_rate:
        review.aggregate_trend = "worsening"
    else:
        review.aggregate_trend = "stable"

    if review.aggregate_trend == "stable":
        review.aggregate_trend_note = (
            f"Critical moments per game stayed flat at {latest_rate:.2f} compared with the previous run."
        )
    elif review.aggregate_trend == "improving":
        review.aggregate_trend_note = (
            f"critical moments per game improved from {previous_rate:.2f} to {latest_rate:.2f} compared with the previous run, meaning fewer critical moments per game."
        )
    else:
        review.aggregate_trend_note = (
            f"critical moments per game worsened from {previous_rate:.2f} to {latest_rate:.2f} compared with the previous run, meaning more critical moments per game."
        )

    return review


def weekly_review_markdown(review: WeeklyReview) -> str:
    if review.total_known_games == 0:
        diagnosis = "No coach history is available yet, so this review cannot claim progress or decline. Start by analysing a recent PGN batch with local state updates enabled."
    elif review.games_analysed == 0:
        diagnosis = (
            f"The latest run contained 0 game(s), but {review.total_known_games} known game(s) remain in local coach history. "
            "Collect a fresh analysed batch before drawing new weekly conclusions."
        )
    else:
        diagnosis = (
            f"Analysed {review.games_analysed} game(s) in the latest run and logged "
            f"{review.critical_moments} critical moment(s) across {review.total_known_games} known game(s)."
        )
        if review.aggregate_trend_note:
            diagnosis = f"{diagnosis} {review.aggregate_trend_note}"

    change_lines: list[str] = []
    if review.aggregate_trend_note:
        change_lines.append(f"- {review.aggregate_trend_note}")
    if review.improved:
        change_lines.extend(["### Improved", *[f"- {item}" for item in review.improved], ""])
    if review.worsened:
        change_lines.extend(["### Worsened", *[f"- {item}" for item in review.worsened], ""])
    if review.stable:
        change_lines.extend(["### Stable", *[f"- {item}" for item in review.stable], ""])
    if not change_lines:
        change_lines = ["- No reliable trend change is available yet.", ""]
    elif change_lines[-1] != "":
        change_lines.append("")

    lines = [
        "# Chess Coach Weekly Review",
        "",
        f"Generated: {review.generated_at.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Executive diagnosis",
        "",
        diagnosis,
        "",
        "## What changed since last review",
        "",
        *change_lines,
        "## Top recurring leaks",
        "",
        *_bullets(review.top_patterns, "No recurring leaks have been ranked yet."),
        "",
        "## Opening notes",
        "",
        *_bullets(review.opening_notes, "No opening family signal is available yet."),
        "",
        "## This week’s training focus",
        "",
        *_bullets(review.worsened or review.top_patterns, "Collect another analysed run before setting a weekly focus."),
        "",
        "## Uncertainty",
        "",
        *_bullets(review.uncertainty_notes, "Trend confidence is acceptable for the currently recorded local history."),
        "",
    ]
    return "\n".join(lines)


def write_weekly_review_markdown(review: WeeklyReview, out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(weekly_review_markdown(review), encoding="utf-8")
    return path
