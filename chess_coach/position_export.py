from __future__ import annotations

from urllib.parse import quote

from .models import AnalysisBundle


def lichess_analysis_url(fen: str) -> str:
    encoded_fen = quote(fen.replace(" ", "_"), safe="/")
    return f"https://lichess.org/analysis/standard/{encoded_fen}?color=white"


def render_position_exports(bundle: AnalysisBundle) -> str:
    lines = ["## Reviewable position exports", ""]
    index = 1
    for game in bundle.games:
        for moment in game.critical_moments:
            lines.append(f"### {index}. {game.event} — move {moment.move_number} {moment.side} `{moment.san}`")
            lines.append("")
            lines.append(f"- Game: `{game.game_id}`")
            lines.append(f"- Phase: `{moment.phase}`")
            lines.append(f"- Classification: `{moment.classification}`")
            lines.append(f"- Played: `{moment.san}`")
            lines.append(f"- Best move: `{moment.best_move or 'unknown'}`")
            lines.append(f"- Eval change: `{moment.eval_change}`")
            if moment.fen_before:
                lines.append(f"- FEN: `{moment.fen_before}`")
                lines.append(f"- Lichess analysis: {lichess_analysis_url(moment.fen_before)}")
            else:
                lines.append("- FEN: `unknown`")
            lines.append("")
            index += 1
    if index == 1:
        lines.append("- None detected.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
