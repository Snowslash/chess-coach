const bridge = window.chessCoachDesktop;
const fallbackMaiaGameTypes = ['rapid', 'blitz', 'bullet', 'classical'];
const fallbackMaiaElo = [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900];
const fallbackUsernamePattern = /^[A-Za-z0-9][A-Za-z0-9_-]{0,28}$/;
function fallbackValidateConfigDraft(config, { requireUsername = false } = {}) {
  const errors = {};
  const warnings = {};
  const username = String(config.default_player || '').trim();
  if (requireUsername && !username) {
    errors.default_player = 'Lichess username is required.';
  } else if (username && !fallbackUsernamePattern.test(username)) {
    errors.default_player = 'Use only letters, numbers, underscore or hyphen.';
  }
  const depth = Number(config.stockfish_depth);
  if (!Number.isInteger(depth) || depth < 1 || depth > 30) errors.stockfish_depth = 'Use an integer from 1 to 30.';
  const timeLimit = Number(config.stockfish_time_limit);
  if (!Number.isFinite(timeLimit) || timeLimit < 0.01 || timeLimit > 30) errors.stockfish_time_limit = 'Use a number from 0.01 to 30.';
  if (!fallbackMaiaGameTypes.includes(String(config.maia2_game_type || '').trim())) errors.maia2_game_type = `Choose one of: ${fallbackMaiaGameTypes.join(', ')}.`;
  if (!fallbackMaiaElo.includes(Number(config.maia2_target_elo))) errors.maia2_target_elo = `Choose one of: ${fallbackMaiaElo.join(', ')}.`;
  for (const [field, value] of [['default_pgn', config.default_pgn], ['default_out', config.default_out]]) {
    if (value && /^(?:[A-Za-z]:\\|\/)/.test(String(value))) warnings[field] = 'Absolute path: valid, but less portable than a project-local path.';
  }
  return { ok: Object.keys(errors).length === 0, errors, warnings };
}
function fallbackDefaultImportedPgnPath(username) {
  const clean = (username || 'player').trim() || 'player';
  return `input/lichess_recent_${clean}.pgn`;
}
function fallbackDefaultAnnotatedPgnPath(username) {
  const clean = (username || 'player').trim() || 'player';
  return `reports/annotated/${clean}_annotated.pgn`;
}
const validationApi = window.ChessCoachValidation || {};
const commandApi = window.ChessCoachCommands || {};
const MAIA_GAME_TYPE_OPTIONS = validationApi.MAIA_GAME_TYPE_OPTIONS || fallbackMaiaGameTypes;
const MAIA_ELO_OPTIONS = validationApi.MAIA_ELO_OPTIONS || fallbackMaiaElo;
const validateConfigDraft = validationApi.validateConfigDraft || fallbackValidateConfigDraft;
const defaultAnnotatedPgnPath = commandApi.defaultAnnotatedPgnPath || fallbackDefaultAnnotatedPgnPath;
const defaultImportedPgnPath = commandApi.defaultImportedPgnPath || fallbackDefaultImportedPgnPath;

const state = {
  bootstrap: null,
  config: null,
  readiness: null,
  lastOutputs: {
    pgn: '',
    report: '',
    json: '',
    annotatedPgn: '',
  },
};

function $(id) {
  return document.getElementById(id);
}

function appendLog(line) {
  const log = $('logOutput');
  log.textContent += `${line}\n`;
  log.scrollTop = log.scrollHeight;
}

function clearMessages() {
  for (const id of ['default_player', 'stockfish_depth', 'stockfish_time_limit', 'maia2_game_type', 'maia2_target_elo']) {
    const el = $(`error-${id}`);
    if (el) el.textContent = '';
  }
  for (const id of ['default_pgn', 'default_out', 'maia2_device']) {
    const el = $(`warning-${id}`);
    if (el) el.textContent = '';
  }
}

function renderValidation(validation) {
  clearMessages();
  for (const [field, message] of Object.entries(validation.errors || {})) {
    const el = $(`error-${field}`);
    if (el) el.textContent = message;
  }
  for (const [field, message] of Object.entries(validation.warnings || {})) {
    const el = $(`warning-${field}`);
    if (el) el.textContent = message;
  }
}

function currentConfigFromForm() {
  return {
    default_player: $('default_player').value.trim(),
    lichess_token: $('lichess_token').value,
    default_pgn: $('default_pgn').value.trim(),
    default_out: $('default_out').value.trim(),
    stockfish_path: $('stockfish_path').value.trim(),
    stockfish_depth: Number($('stockfish_depth').value),
    stockfish_time_limit: Number($('stockfish_time_limit').value),
    maia2_enabled: $('maia2_enabled').checked,
    maia2_game_type: $('maia2_game_type').value,
    maia2_device: $('maia2_device').value.trim(),
    maia2_target_elo: Number($('maia2_target_elo').value),
  };
}

function syncWorkflowDefaults() {
  const username = $('default_player').value.trim();
  if (!$('import_out_path').dataset.manual) {
    $('import_out_path').value = defaultImportedPgnPath(username);
  }
  if (!$('analyse_pgn_path').dataset.manual && $('import_out_path').value) {
    $('analyse_pgn_path').value = $('import_out_path').value;
  }
  if (!$('analyse_out_path').dataset.manual) {
    $('analyse_out_path').value = $('default_out').value.trim() || 'reports/latest.md';
  }
  const reportPath = $('analyse_out_path').value.trim();
  if (!$('export_json_path').dataset.manual && reportPath) {
    $('export_json_path').value = reportPath.replace(/\.md$/i, '.json');
  }
  if (!$('export_out_path').dataset.manual) {
    $('export_out_path').value = defaultAnnotatedPgnPath(username);
  }
}

function fillForm(config) {
  state.config = config;
  $('default_player').value = config.default_player || '';
  $('lichess_token').value = config.lichess_token || '';
  $('default_pgn').value = config.default_pgn || 'input/sample_games.pgn';
  $('default_out').value = config.default_out || 'reports/latest.md';
  $('stockfish_path').value = config.stockfish_path || '';
  $('stockfish_depth').value = config.stockfish_depth;
  $('stockfish_time_limit').value = config.stockfish_time_limit;
  $('maia2_enabled').checked = Boolean(config.maia2_enabled);
  $('maia2_game_type').value = config.maia2_game_type;
  $('maia2_device').value = config.maia2_device;
  $('maia2_target_elo').value = String(config.maia2_target_elo);
  syncWorkflowDefaults();
}

function populateSelects() {
  $('maia2_game_type').innerHTML = MAIA_GAME_TYPE_OPTIONS.map((value) => `<option value="${value}">${value}</option>`).join('');
  $('maia2_target_elo').innerHTML = MAIA_ELO_OPTIONS.map((value) => `<option value="${value}">${value}</option>`).join('');
}

function renderStatusCards(readiness, lichess = null) {
  const host = $('statusCards');
  const template = $('statusTemplate');
  host.innerHTML = '';
  const entries = [
    ['Stockfish', readiness?.stockfish],
    ['Maia 2', readiness?.maia],
  ];
  if (lichess) {
    entries.push(['Lichess', lichess]);
  }
  for (const [name, data] of entries) {
    if (!data) continue;
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector('.status-name').textContent = name;
    const pill = node.querySelector('.status-pill');
    pill.textContent = data.status || (data.ok ? 'available' : 'unknown');
    pill.classList.add(data.status || 'available');
    node.querySelector('.status-details').textContent = data.details || data.message || '';
    host.appendChild(node);
  }
}

function renderFirstRunNotice(exists) {
  const notice = $('firstRunNotice');
  if (exists) {
    notice.classList.add('hidden');
    notice.textContent = '';
    return;
  }
  notice.classList.remove('hidden');
  notice.textContent = 'First run: .env.stockfish does not exist yet. Use “Create config from defaults”, then save your local paths and username.';
}

function setOutputPaths(paths) {
  const host = $('outputPaths');
  host.innerHTML = '';
  for (const [label, value] of Object.entries(paths)) {
    if (!value) continue;
    const row = document.createElement('div');
    row.className = 'status-card';
    const labelEl = document.createElement('strong');
    labelEl.textContent = label;
    const valueEl = document.createElement('div');
    valueEl.textContent = value;
    row.append(labelEl, valueEl);
    row.addEventListener('click', () => bridge.openPath(value));
    host.appendChild(row);
  }
}

async function loadConfig() {
  const response = await bridge.loadConfig();
  renderFirstRunNotice(response.exists);
  renderValidation(response.validation);
  fillForm(response.config);
}

async function saveConfig() {
  const draft = currentConfigFromForm();
  const validation = validateConfigDraft(draft);
  renderValidation(validation);
  if (!validation.ok) {
    appendLog('Save blocked: fix the highlighted settings first.');
    return;
  }
  const result = await bridge.saveConfig(draft);
  if (!result.ok) {
    renderValidation(result.validation);
    appendLog('Save blocked at the Python boundary.');
    return;
  }
  appendLog(`Saved settings to ${result.path}`);
  renderFirstRunNotice(true);
}

async function testReadiness() {
  const readiness = await bridge.testReadiness();
  state.readiness = readiness;
  renderStatusCards(readiness);
}

async function testLichess() {
  const username = $('default_player').value.trim();
  if (!username) {
    appendLog('Lichess test blocked: enter a username first.');
    return;
  }
  const result = await bridge.testLichess({ username, token: $('lichess_token').value });
  renderStatusCards(state.readiness, result);
}

function attachAutoValidation() {
  for (const id of ['default_player', 'default_pgn', 'default_out', 'stockfish_depth', 'stockfish_time_limit', 'maia2_game_type', 'maia2_device', 'maia2_target_elo']) {
    $(id).addEventListener('input', () => {
      renderValidation(validateConfigDraft(currentConfigFromForm()));
      syncWorkflowDefaults();
    });
  }
}

function markManual(id) {
  $(id).addEventListener('input', () => {
    $(id).dataset.manual = 'true';
  });
}

async function exportSettings() {
  const includeToken = window.confirm('Export with the real token included? Choose Cancel for the safer redacted export.');
  const result = await bridge.exportSettings({ config: currentConfigFromForm(), redactToken: !includeToken });
  if (!result.cancelled && result.ok) {
    appendLog(`Exported settings to ${result.path}`);
  }
}

async function importSettings() {
  const result = await bridge.previewSettingsImport({});
  if (!result.ok || result.cancelled) {
    return;
  }
  renderValidation(result.preview.validation);
  const proceed = window.confirm(`Preview ${result.sourcePath}\n\nApply these settings to .env.stockfish?`);
  if (!proceed) {
    return;
  }
  const saveResult = await bridge.applyImportedSettings({ config: result.preview.config });
  if (saveResult.ok) {
    appendLog(`Imported settings from ${result.sourcePath}`);
    await loadConfig();
  }
}

async function createDiagnosticBundle() {
  const result = await bridge.createDiagnosticBundle({
    readiness: state.readiness,
    includeReport: $('diagnosticIncludeReport').checked,
    includePgn: $('diagnosticIncludePgn').checked,
    selectedPaths: {
      pgn: $('analyse_pgn_path').value.trim(),
      report: $('analyse_out_path').value.trim(),
    },
    token: $('lichess_token').value,
  });
  if (result.ok) {
    appendLog(`Created diagnostic bundle at ${result.path}`);
  }
}

async function importRecentGames() {
  const payload = {
    username: $('default_player').value.trim(),
    maxGames: Number($('import_max_games').value),
    perf: $('import_perf').value,
    ratedOnly: $('import_rated_only').checked,
    sinceDays: Number($('import_since_days').value),
    outPath: $('import_out_path').value.trim(),
  };
  const result = await bridge.importLichess(payload);
  if (!result.ok) {
    appendLog(result.validation ? JSON.stringify(result.validation.errors) : result.stderr || 'Import failed.');
    return;
  }
  $('analyse_pgn_path').value = result.outPath;
  state.lastOutputs.pgn = result.outPath;
  appendLog(`Imported PGN: ${result.outPath}`);
}

async function analyseGames() {
  const payload = {
    username: $('default_player').value.trim(),
    pgnPath: $('analyse_pgn_path').value.trim(),
    outPath: $('analyse_out_path').value.trim(),
  };
  const result = await bridge.analyseGames(payload);
  if (!result.ok) {
    appendLog(result.validation ? JSON.stringify(result.validation.errors) : result.stderr || 'Analysis failed.');
    return;
  }
  $('export_json_path').value = result.jsonPath;
  state.lastOutputs.report = result.markdownPath;
  state.lastOutputs.json = result.jsonPath;
  setOutputPaths({ 'Markdown report': result.markdownPath, 'Structured JSON': result.jsonPath });
}

async function exportAnnotatedPgn() {
  const payload = {
    jsonPath: $('export_json_path').value.trim(),
    outPath: $('export_out_path').value.trim(),
    maxGames: Number($('export_max_games').value),
    criticalOnly: $('export_critical_only').checked,
  };
  const result = await bridge.exportAnnotatedPgn(payload);
  if (!result.ok) {
    appendLog(result.validation ? JSON.stringify(result.validation.errors) : result.stderr || 'Annotated PGN export failed.');
    return;
  }
  state.lastOutputs.annotatedPgn = result.outPath;
  setOutputPaths({
    'Markdown report': $('analyse_out_path').value.trim(),
    'Structured JSON': $('export_json_path').value.trim(),
    'Annotated PGN': result.outPath,
  });
}

function bindButtons() {
  $('saveConfigButton').addEventListener('click', saveConfig);
  $('createDefaultsButton').addEventListener('click', async () => {
    await loadConfig();
    appendLog('Loaded default settings into the form. Save when ready.');
  });
  $('resetDefaultsButton').addEventListener('click', () => {
    fillForm({
      default_player: '',
      lichess_token: '',
      default_pgn: 'input/sample_games.pgn',
      default_out: 'reports/latest.md',
      stockfish_path: '',
      stockfish_depth: 12,
      stockfish_time_limit: 0.1,
      maia2_enabled: false,
      maia2_game_type: 'rapid',
      maia2_device: 'cpu',
      maia2_target_elo: 1500,
    });
    appendLog('Reset form to defaults. Save to write them to .env.stockfish.');
  });
  $('testReadinessButton').addEventListener('click', testReadiness);
  $('testLichessButton').addEventListener('click', testLichess);
  $('browsePgnButton').addEventListener('click', async () => {
    const value = await bridge.pickPath({ purpose: 'pgnInput', currentValue: $('default_pgn').value });
    if (value) $('default_pgn').value = value;
  });
  $('browseReportButton').addEventListener('click', async () => {
    const value = await bridge.pickPath({ purpose: 'markdownOutput', currentValue: $('default_out').value });
    if (value) $('default_out').value = value;
  });
  $('exportSettingsButton').addEventListener('click', exportSettings);
  $('importSettingsButton').addEventListener('click', importSettings);
  $('diagnosticBundleButton').addEventListener('click', createDiagnosticBundle);
  $('importGamesButton').addEventListener('click', importRecentGames);
  $('analyseGamesButton').addEventListener('click', analyseGames);
  $('exportPgnButton').addEventListener('click', exportAnnotatedPgn);
  $('clearLogButton').addEventListener('click', () => {
    $('logOutput').textContent = '';
  });
  for (const button of document.querySelectorAll('[data-link]')) {
    button.addEventListener('click', () => bridge.openExternal(button.dataset.link));
  }
}

async function setupPathDefaults() {
  for (const id of ['import_out_path', 'analyse_pgn_path', 'analyse_out_path', 'export_json_path', 'export_out_path']) {
    markManual(id);
  }
}

async function init() {
  populateSelects();
  bindButtons();
  attachAutoValidation();
  setupPathDefaults();
  if (!bridge) {
    appendLog('Desktop bridge did not load. Restart the app after reinstalling dependencies; if this persists, open DevTools and check preload errors.');
    return;
  }
  const bootstrap = await bridge.getBootstrap();
  state.bootstrap = bootstrap;
  $('configPath').textContent = bootstrap.configPath;
  bridge.onLog((entry) => appendLog(`[${entry.timestamp}] ${entry.label}: ${entry.message}`));
  await loadConfig();
  await testReadiness();
}

init().catch((error) => {
  appendLog(`Fatal startup error: ${error.stack || error.message}`);
});
