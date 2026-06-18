(() => {
function defaultImportedPgnPath(username) {
  const clean = (username || 'player').trim() || 'player';
  return `input/lichess_recent_${clean}.pgn`;
}

function defaultAnnotatedPgnPath(username) {
  const clean = (username || 'player').trim() || 'player';
  return `reports/annotated/${clean}_annotated.pgn`;
}

function buildGuiSupportArgs(action, envFile = null, extraArgs = []) {
  const args = ['-m', 'chess_coach.gui_support', action];
  if (envFile) {
    args.push('--env-file', envFile);
  }
  args.push(...extraArgs);
  return args;
}

function buildImportLichessArgs(payload) {
  const args = ['-m', 'chess_coach', 'import-lichess', '--user', payload.username, '--max', String(payload.maxGames), '--out', payload.outPath];
  if (payload.perf) {
    args.push('--perf', payload.perf);
  }
  if (payload.ratedOnly) {
    args.push('--rated-only');
  }
  if (payload.sinceDays) {
    args.push('--since-days', String(payload.sinceDays));
  }
  return args;
}

function buildAnalyseArgs(payload) {
  const args = ['-m', 'chess_coach', 'analyse', '--pgn', payload.pgnPath, '--out', payload.outPath, '--player', payload.username, '--update-state'];
  return args;
}

function buildExportAnnotatedArgs(payload) {
  const args = ['-m', 'chess_coach', 'export-annotated-pgn', '--from', payload.jsonPath, '--out', payload.outPath, '--max-games', String(payload.maxGames)];
  if (payload.criticalOnly !== false) {
    args.push('--critical-only');
  }
  return args;
}

const exported = {
  buildAnalyseArgs,
  buildExportAnnotatedArgs,
  buildGuiSupportArgs,
  buildImportLichessArgs,
  defaultAnnotatedPgnPath,
  defaultImportedPgnPath,
};

if (typeof module !== 'undefined') {
  module.exports = exported;
}

if (typeof window !== 'undefined') {
  window.ChessCoachCommands = exported;
}
})();
