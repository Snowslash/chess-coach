from __future__ import annotations
from datetime import datetime
from pathlib import Path
from .models import AnalysisBundle
from .position_export import render_position_exports

def default_json_path(markdown_path): return Path(markdown_path).with_suffix('.json')
def write_json(bundle:AnalysisBundle,path):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(bundle.model_dump_json(indent=2),encoding='utf-8'); return p
def write_markdown_report(bundle, markdown_path, json_path):
    p=Path(markdown_path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(render_markdown(bundle,json_path,p),encoding='utf-8'); return p
def _bullets(items): return [f'- {x}' for x in items] if items else ['- None detected.']
def _numbered(items): return [f'{i}. {x}' for i,x in enumerate(items,1)] if items else ['1. None.']
def _is_player_move(game, move): return game.player_colour is None or move.side == game.player_colour
def _important(games):
    rows=[]
    for g in games:
        for m in g.moves:
            if m.classification!='book/neutral' and _is_player_move(g,m): rows.append((abs(m.eval_change or 0),f'- {g.event} ({g.date}), move {m.move_number} {m.side}: {m.san} — {m.classification}, eval change {m.eval_change}, best `{m.best_move or "unknown"}`'))
    return [r for _,r in sorted(rows, key=lambda x:x[0], reverse=True)[:10]] or ['- None detected.']
def _crit(games):
    rows=[]
    for g in games:
        for m in g.critical_moments:
            row=f'- `{g.game_id}` move {m.move_number} {m.side} `{m.san}` ({m.phase}): {m.classification}; eval change {m.eval_change}; best `{m.best_move or "unknown"}`'
            if m.fen_before:
                row += f'\n  - FEN: `{m.fen_before}`'
            rows.append(row)
    return rows[:20] or ['- None detected.']

def _pct(value): return f'{value * 100:.1f}%'

def _maia2_scored_player_moves(bundle):
    rows=[]
    for g in bundle.games:
        player_moves=[m for m in g.moves if _is_player_move(g,m)]
        for m in player_moves:
            if m.maia2_played_move_prob is not None:
                rows.append((g,m,len(player_moves)))
    return rows

def _maia2_move_row(g, m):
    details=[]
    if m.maia2_played_move_prob is not None:
        details.append(f'played {_pct(m.maia2_played_move_prob)}')
    if m.maia2_top_moves:
        top_move, top_prob=next(iter(m.maia2_top_moves.items()))
        details.append(f'top Maia 2 `{top_move}` {_pct(top_prob)}')
    if m.maia2_win_prob is not None:
        details.append(f'win probability {_pct(m.maia2_win_prob)}')
    if m.eval_change is not None:
        details.append(f'eval change {m.eval_change}')
    if m.best_move:
        details.append(f'best `{m.best_move}`')
    suffix=': ' + '; '.join(details) if details else ''
    return f'- `{g.game_id}` move {m.move_number} {m.side} `{m.san}` — {m.classification}{suffix}'

def _maia2_ranked_bad_moves(scored_moves, *, max_probability=None, min_probability=None, limit=10):
    candidates=[]
    for g,m,_ in scored_moves:
        if m.classification == 'book/neutral' or m.eval_change is None or m.maia2_played_move_prob is None:
            continue
        if max_probability is not None and m.maia2_played_move_prob >= max_probability:
            continue
        if min_probability is not None and m.maia2_played_move_prob < min_probability:
            continue
        candidates.append((abs(m.eval_change), g, m))
    return [_maia2_move_row(g,m) for _,g,m in sorted(candidates, key=lambda x:x[0], reverse=True)[:limit]]

def _maia2_opening_style_rows(scored_moves, limit=8):
    candidates=[]
    for g,m,_ in scored_moves:
        if (
            m.phase == 'opening'
            and m.classification != 'book/neutral'
            and m.maia2_played_move_prob is not None
            and m.maia2_played_move_prob < 0.10
        ):
            candidates.append((m.maia2_played_move_prob, g, m))
    return [_maia2_move_row(g,m) for _,g,m in sorted(candidates, key=lambda x:x[0])[:limit]]

def _maia2_rows(bundle, json_path=None):
    if not bundle.metadata.get('maia2_available'):
        return ['- Maia 2 not available for this run.']
    rows=[]
    target_elo=bundle.metadata.get('maia2_target_elo')
    if target_elo:
        rows.append(f'- Target comparison: target Elo {target_elo}.')
    scored=_maia2_scored_player_moves(bundle)
    total_player_moves=sum(1 for g in bundle.games for m in g.moves if _is_player_move(g,m))
    probs=[m.maia2_played_move_prob for _,m,_ in scored if m.maia2_played_move_prob is not None]
    if not probs:
        return rows + ['- No Maia 2 move probabilities recorded.']
    sorted_probs=sorted(probs)
    mid=len(sorted_probs)//2
    median=sorted_probs[mid] if len(sorted_probs)%2 else (sorted_probs[mid-1]+sorted_probs[mid])/2
    rows.append(
        f'- Player moves scored: {len(probs)}/{total_player_moves}; '
        f'mean played-move probability {_pct(sum(probs)/len(probs))}; '
        f'median {_pct(median)}; under 5%: {sum(p < 0.05 for p in probs)}; under 2%: {sum(p < 0.02 for p in probs)}.'
    )
    bad_unlikely=_maia2_ranked_bad_moves(scored, max_probability=0.15)
    human_likely=_maia2_ranked_bad_moves(scored, min_probability=0.50)
    opening_style=_maia2_opening_style_rows(scored)
    rows.extend(['','### Bad + Maia-unlikely moves','',*(bad_unlikely or ['- None detected.'])])
    rows.extend(['','### Bad but Maia-human-likely moves','',*(human_likely or ['- None detected.'])])
    rows.extend(['','### Opening repertoire/style observations','',*(opening_style or ['- None detected.'])])
    if json_path:
        rows.extend(['',f'- Full per-move Maia data is in `{json_path}`.'])
    return rows

def render_markdown(bundle, json_path, markdown_path=None):
    p=bundle.patterns
    if p.critical_moments==0:
        exec_diag = 'No critical moments were detected. If this was a mock run, install/configure Stockfish before drawing chess conclusions.'
    else:
        top_priority = p.training_priorities[0].rstrip('.') if p.training_priorities else 'review the listed critical moments'
        exec_diag = f'Analysed {p.games_analysed} game(s) and found {p.critical_moments} critical moment(s). Top priority: {top_priority}.'
    uncertainty_notes = list(p.uncertainty_notes)
    if bundle.metadata.get('maia2_enabled') and not bundle.metadata.get('maia2_available'):
        uncertainty_notes.append(f"Maia 2 human-likeness analysis requested but unavailable: {bundle.metadata.get('maia2_reason')}")
    elif bundle.metadata.get('maia2_available'):
        uncertainty_notes.append('Maia 2 human-likeness scoring is available for moves with recorded Maia 2 probabilities.')
    lines=['# Chess Coach Report','',f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}',f'PGNs analysed: {bundle.source_pgn}',f'Games analysed: {p.games_analysed}','','## Executive diagnosis','',exec_diag,'','## Recurring weaknesses','',*_bullets(p.recurring_weaknesses),'','## Most important mistakes','',*_important(bundle.games),'','## Opening notes','',*_bullets(p.opening_notes),'','## Middlegame notes','',*_bullets(p.middlegame_notes),'','## Endgame notes','',*_bullets(p.endgame_notes),'','## Training priorities','',*_numbered(p.training_priorities),'','## 7-day training plan','',*_bullets(p.training_plan_7_days)]
    if bundle.metadata.get('maia2_enabled'):
        lines.extend(['','## Maia 2 human-likeness','',*_maia2_rows(bundle,json_path)])
    lines.extend(['','## Critical positions to review','',*_crit(bundle.games),'','## Uncertainty / limits','',*_bullets(uncertainty_notes),'','## Raw files','',f'- JSON: `{json_path}`',f'- PGN: `{bundle.source_pgn}`'])
    if markdown_path: lines.append(f'- Markdown: `{markdown_path}`')
    lines.extend(['', render_position_exports(bundle).rstrip()])
    return '\n'.join(lines).rstrip() + '\n'
