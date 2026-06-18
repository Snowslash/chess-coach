(() => {
const MAIA_GAME_TYPE_OPTIONS = ['rapid', 'blitz', 'bullet', 'classical'];
const MAIA_DEVICE_OPTIONS = ['cpu', 'cuda', 'mps'];
const MAIA_ELO_OPTIONS = [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900];
const SAFE_LICHESS_USERNAME = /^[A-Za-z0-9][A-Za-z0-9_-]{0,28}$/;

function validateConfigDraft(config, { requireUsername = false } = {}) {
  const errors = {};
  const warnings = {};
  const username = String(config.default_player || '').trim();
  if (requireUsername && !username) {
    errors.default_player = 'Lichess username is required.';
  } else if (username && !SAFE_LICHESS_USERNAME.test(username)) {
    errors.default_player = 'Use only letters, numbers, underscore or hyphen.';
  }

  const depth = Number(config.stockfish_depth);
  if (!Number.isInteger(depth) || depth < 1 || depth > 30) {
    errors.stockfish_depth = 'Use an integer from 1 to 30.';
  }

  const timeLimit = Number(config.stockfish_time_limit);
  if (!Number.isFinite(timeLimit) || timeLimit < 0.01 || timeLimit > 30) {
    errors.stockfish_time_limit = 'Use a number from 0.01 to 30.';
  }

  const gameType = String(config.maia2_game_type || '').trim();
  if (!MAIA_GAME_TYPE_OPTIONS.includes(gameType)) {
    errors.maia2_game_type = `Choose one of: ${MAIA_GAME_TYPE_OPTIONS.join(', ')}.`;
  }

  const elo = Number(config.maia2_target_elo);
  if (!MAIA_ELO_OPTIONS.includes(elo)) {
    errors.maia2_target_elo = `Choose one of: ${MAIA_ELO_OPTIONS.join(', ')}.`;
  }

  const device = String(config.maia2_device || '').trim();
  if (device && !MAIA_DEVICE_OPTIONS.includes(device)) {
    warnings.maia2_device = `Unknown device '${device}'. Standard options are: ${MAIA_DEVICE_OPTIONS.join(', ')}.`;
  }

  for (const [field, value] of [['default_pgn', config.default_pgn], ['default_out', config.default_out]]) {
    if (value && /^(?:[A-Za-z]:\\|\/)/.test(String(value))) {
      warnings[field] = 'Absolute path: valid, but less portable than a project-local path.';
    }
  }

  return { ok: Object.keys(errors).length === 0, errors, warnings };
}

function validateWorkflowInput(kind, payload) {
  if (kind === 'import') {
    if (!SAFE_LICHESS_USERNAME.test(String(payload.username || '').trim())) {
      return { ok: false, errors: { username: 'Use a valid Lichess username.' } };
    }
  }
  if (kind === 'analyse') {
    if (!payload.pgnPath) {
      return { ok: false, errors: { pgnPath: 'Choose or import a PGN first.' } };
    }
    if (!payload.outPath) {
      return { ok: false, errors: { outPath: 'Choose an output report path.' } };
    }
  }
  if (kind === 'export') {
    if (!payload.jsonPath) {
      return { ok: false, errors: { jsonPath: 'Analyse games before exporting annotated PGN.' } };
    }
    if (!payload.outPath) {
      return { ok: false, errors: { outPath: 'Choose an annotated PGN output path.' } };
    }
    const maxGames = Number(payload.maxGames);
    if (!Number.isInteger(maxGames) || maxGames < 1) {
      return { ok: false, errors: { maxGames: 'Use a whole number of games to export.' } };
    }
  }
  return { ok: true, errors: {} };
}

const exported = {
  MAIA_GAME_TYPE_OPTIONS,
  MAIA_DEVICE_OPTIONS,
  MAIA_ELO_OPTIONS,
  SAFE_LICHESS_USERNAME,
  validateConfigDraft,
  validateWorkflowInput,
};

if (typeof module !== 'undefined') {
  module.exports = exported;
}

if (typeof window !== 'undefined') {
  window.ChessCoachValidation = exported;
}
})();
