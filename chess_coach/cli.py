from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .annotated_pgn import count_games_to_export, render_annotated_pgn
from .flashcards import cards_from_bundle, write_cards_markdown
from .lichess_import import fetch_recent_games
from .lichess_study import LichessStudyError, create_study, import_pgn_to_study, token_from_env
from .models import AnalysisBundle
from .pipeline import analyse_pgn
from .report_writer import default_json_path
from .training_plan import build_training_plan, write_training_plan_markdown
from .weekly_review import build_weekly_review, write_weekly_review_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m chess_coach",
        description="Hermes Chess Coach MVP",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    analyse = sub.add_parser("analyse", help="Analyse PGN games and generate JSON + Markdown report")
    analyse.add_argument("--pgn", required=True, help="Input PGN file. Relative paths are resolved from the current directory.")
    analyse.add_argument("--out", required=True, help="Output Markdown report path")
    analyse.add_argument("--player", default=None, help="Player name to identify colour, optional")
    analyse.add_argument("--mock", action="store_true", help="Force mock mode even if Stockfish is available")
    analyse.add_argument(
        "--update-state",
        action="store_true",
        help="Update local longitudinal coach state after analysis",
    )
    analyse.add_argument(
        "--state-path",
        default=".coach/state.json",
        help="Local coach state path, default .coach/state.json",
    )
    lichess = sub.add_parser("import-lichess", help="Import recent public Lichess games as PGN")
    lichess.add_argument("--user", required=True, help="Lichess username")
    lichess.add_argument("--max", type=int, default=20, help="Maximum games to import")
    lichess.add_argument("--perf", default=None, help="Optional Lichess perf type filter, e.g. rapid")
    lichess.add_argument("--rated-only", action="store_true", help="Only import rated games")
    lichess.add_argument("--since-days", type=int, default=None, help="Only import games from the last N days")
    lichess.add_argument("--out", default="input/lichess_recent.pgn", help="Output PGN path")
    cards = sub.add_parser("cards", help="Generate review cards from report JSON")
    cards.add_argument("--from", dest="from_json", required=True, help="Input analysis JSON path")
    cards.add_argument("--out", required=True, help="Output Markdown path")
    annotated = sub.add_parser("export-annotated-pgn", help="Export local annotated PGN from analysis JSON")
    annotated.add_argument("--from", dest="from_json", required=True, help="Input analysis JSON path")
    annotated.add_argument("--out", required=True, help="Output annotated PGN path")
    annotated.add_argument("--max-games", type=int, default=None, help="Maximum games to export")
    annotated.add_argument(
        "--critical-only",
        action="store_true",
        default=True,
        help="Annotate only critical moments (default)",
    )
    annotated.add_argument(
        "--include-all-moves",
        action="store_true",
        help="Also annotate non-critical analysed moves when useful",
    )
    weekly = sub.add_parser("weekly-review", help="Generate a longitudinal weekly coach review from local state")
    weekly.add_argument("--state-path", default=".coach/state.json")
    weekly.add_argument("--out", default="reports/weekly_review.md")
    training = sub.add_parser("training-plan", help="Generate measurable training plan from report JSON")
    training.add_argument("--from", dest="from_json", required=True)
    training.add_argument("--out", default="reports/training_plan.md")
    study_create = sub.add_parser("lichess-study-create", help="Create a private or unlisted Lichess Study")
    study_create.add_argument("--name", required=True, help="Study name")
    study_create.add_argument("--visibility", choices=("private", "unlisted"), default="private")
    study_create.add_argument("--token-env", default="LICHESS_TOKEN", help="Environment variable holding the Lichess OAuth token")
    study_import = sub.add_parser("lichess-study-import", help="Import annotated PGN into an existing Lichess Study")
    study_import.add_argument("--study-id", required=True, help="Target Lichess Study ID")
    study_import.add_argument("--pgn", required=True, help="Annotated PGN file to import")
    study_import.add_argument("--name", default=None, help="Optional chapter name for single-game PGN imports")
    study_import.add_argument("--orientation", choices=("white", "black"), default="white")
    study_import.add_argument("--variant", default=None)
    study_import.add_argument("--mode", choices=("practice", "conceal", "gamebook"), default=None)
    study_import.add_argument("--token-env", default="LICHESS_TOKEN", help="Environment variable holding the Lichess OAuth token")
    return parser


def _missing_pgn_message(pgn: Path) -> str:
    cwd = Path.cwd()
    input_dir = cwd / "input"
    lines = [
        f"PGN not found: {pgn}",
        f"Current directory: {cwd}",
    ]
    if input_dir.exists():
        pgns = sorted(input_dir.glob("*.pgn"))
        if pgns:
            lines.append("PGN files currently in ./input:")
            lines.extend(f"  - input/{item.name}" for item in pgns)
            lines.append("Example:")
            lines.append(f"  python -m chess_coach analyse --pgn 'input/{pgns[0].name}' --out reports/latest.md")
        else:
            lines.append("./input exists but contains no .pgn files. Put your game there or pass the full PGN path.")
    else:
        lines.append("No ./input directory found. Either run from the project root or pass an absolute PGN path.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "analyse":
        pgn = Path(args.pgn)
        if not pgn.exists():
            print(_missing_pgn_message(pgn), file=sys.stderr)
            return 2
        out = Path(args.out)
        bundle = analyse_pgn(pgn, out, player=args.player, mock=args.mock)
        if args.update_state:
            from .history import load_state, save_state, update_state_from_bundle

            state_path = Path(args.state_path)
            state = load_state(state_path)
            state = update_state_from_bundle(state, bundle)
            save_state(state, state_path)
            print(f"Updated coach state: {state_path}")
        print(f"Markdown report: {out}")
        print(f"Structured JSON: {default_json_path(out)}")
        if any(not game.stockfish_available for game in bundle.games):
            print("Stockfish not used for at least one game. Set STOCKFISH_PATH or install stockfish for real engine analysis.")
        return 0
    if args.command == "import-lichess":
        out = fetch_recent_games(
            args.user,
            Path(args.out),
            max_games=args.max,
            perf=args.perf,
            rated_only=args.rated_only,
            since_days=args.since_days,
        )
        print(f"Imported Lichess PGN: {out}")
        print(f"Analyse it with: python -m chess_coach analyse --pgn '{out}' --out reports/latest.md --player {args.user}")
        return 0
    if args.command == "cards":
        bundle = AnalysisBundle.model_validate_json(Path(args.from_json).read_text(encoding="utf-8"))
        cards = cards_from_bundle(bundle)
        out = write_cards_markdown(cards, args.out)
        print(f"Generated {len(cards)} review card(s): {out}")
        return 0
    if args.command == "export-annotated-pgn":
        source = Path(args.from_json)
        if not source.exists():
            print(f"Analysis JSON not found: {source}", file=sys.stderr)
            return 2
        if args.max_games is not None and args.max_games < 0:
            print("--max-games must be >= 0", file=sys.stderr)
            return 2
        bundle = AnalysisBundle.model_validate_json(source.read_text(encoding="utf-8"))
        try:
            rendered = render_annotated_pgn(
                bundle,
                max_games=args.max_games,
                critical_only=args.critical_only,
                include_all_moves=args.include_all_moves,
            )
            exported_games = count_games_to_export(bundle, max_games=args.max_games)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"Annotated PGN: {out}")
        print(f"Games exported: {exported_games}")
        return 0
    if args.command == "weekly-review":
        from .history import load_state

        state = load_state(Path(args.state_path))
        review = build_weekly_review(state)
        out = write_weekly_review_markdown(review, args.out)
        print(f"Generated weekly review: {out}")
        return 0
    if args.command == "training-plan":
        bundle = AnalysisBundle.model_validate_json(Path(args.from_json).read_text(encoding="utf-8"))
        cards = cards_from_bundle(bundle)
        plan = build_training_plan(bundle, cards)
        out = write_training_plan_markdown(plan, args.out)
        print(f"Generated training plan: {out}")
        return 0
    if args.command == "lichess-study-create":
        try:
            token = token_from_env(args.token_env)
            study = create_study(token=token, name=args.name, visibility=args.visibility)
        except (LichessStudyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"Study ID: {study.id}")
        print(f"Study URL: {study.url}")
        return 0
    if args.command == "lichess-study-import":
        pgn_path = Path(args.pgn)
        if not pgn_path.exists():
            print(f"PGN not found: {pgn_path}", file=sys.stderr)
            return 2
        try:
            token = token_from_env(args.token_env)
            result = import_pgn_to_study(
                token=token,
                study_id=args.study_id,
                pgn=pgn_path.read_text(encoding="utf-8"),
                name=args.name,
                orientation=args.orientation,
                variant=args.variant,
                mode=args.mode,
            )
        except (LichessStudyError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(f"Study URL: {result.study_url}")
        print(f"Chapters imported: {len(result.chapters)}")
        for chapter in result.chapters:
            print(f"Chapter: {chapter.name}")
            print(f"Chapter URL: {chapter.url}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
