from __future__ import annotations

from pathlib import Path

from .config import ChessCoachConfig, load_config
from .maia2_analyser import annotate_games_with_maia2, load_maia2_runtime, maia2_available
from .models import AnalysisBundle
from .pattern_detector import detect_patterns
from .pgn_parser import parse_pgn_file
from .report_writer import default_json_path, write_json, write_markdown_report
from .stockfish_analyser import analyse_game


def analyse_pgn(
    pgn_path: str | Path,
    out_path: str | Path,
    player: str | None = None,
    mock: bool = False,
    *,
    config: ChessCoachConfig | None = None,
    maia2_save_root: str | Path | None = None,
) -> AnalysisBundle:
    """Analyse using one config snapshot and the caller's input/output paths.

    CLI callers may omit config/cache context to retain the existing defaults.
    Web callers supply their validated config and absolute project-local paths,
    including the Maia model directory rather than relying on process cwd.
    """
    cfg = config if config is not None else load_config()
    parsed = parse_pgn_file(pgn_path, player=player or cfg.default_player)
    analyses = [analyse_game(game, cfg, mock=mock) for game in parsed]
    patterns = detect_patterns(analyses)
    maia2 = maia2_available(cfg)
    maia2_reason = maia2.reason
    if maia2.available:
        try:
            maia2_model, maia2_prepared, maia2_inference_each = load_maia2_runtime(cfg, save_root=maia2_save_root)
            annotate_games_with_maia2(analyses, maia2_model, maia2_prepared, cfg.maia2_target_elo, maia2_inference_each)
        except Exception as exc:
            maia2 = type(maia2)(enabled=True, available=False, reason=f'Maia 2 runtime failed: {exc}')
            maia2_reason = maia2.reason
    bundle = AnalysisBundle(
        source_pgn=str(pgn_path),
        games=analyses,
        patterns=patterns,
        metadata={
            'stockfish_path': cfg.stockfish_path,
            'stockfish_depth': cfg.stockfish_depth,
            'stockfish_time_limit': cfg.stockfish_time_limit,
            'mock_requested': mock,
            'maia2_enabled': maia2.enabled,
            'maia2_available': maia2.available,
            'maia2_reason': maia2_reason,
            'maia2_game_type': cfg.maia2_game_type,
            'maia2_device': cfg.maia2_device,
            'maia2_target_elo': cfg.maia2_target_elo,
        },
    )
    json_path = default_json_path(out_path)
    write_json(bundle, json_path)
    write_markdown_report(bundle, out_path, json_path)
    return bundle
