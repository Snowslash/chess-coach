const state = {
  bootstrap: null,
  config: null,
  readiness: null,
  options: {
    maia_game_types: ['rapid', 'blitz', 'bullet', 'classical'],
    maia_elo: [1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
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

function defaultImportedPgnPath(username) {
  const clean = (username || 'player').trim() || 'player';
  return `input/lichess_recent_${clean}.pgn`;
}

function defaultAnnotatedPgnPath(username) {
  const clean = (username || 'player').trim() || 'player';
  return `reports/annotated/${clean}_annotated.pgn`;
}

function syncWorkflowDefaults() {
  const username = $('default_player').value.trim();
  if (!$('import_out_path').dataset.manual) {
    $('import_out_path').value = defaultImportedPgnPath(username);
  }
  if (!$('analyse_pgn_path').dataset.manual) {
    $('analyse_pgn_path').value = $('import_out_path').value;
  }
  if (!$('analyse_out_path').dataset.manual) {
    $('analyse_out_path').value = $('default_out').value.trim() || 'reports/latest.md';
  }
  if (!$('export_json_path').dataset.manual) {
    $('export_json_path').value = $('analyse_out_path').value.replace(/\.md$/i, '.json');
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
  $('maia2_game_type').innerHTML = state.options.maia_game_types.map((value) => `<option value="${value}">${value}</option>`).join('');
  $('maia2_target_elo').innerHTML = state.options.maia_elo.map((value) => `<option value="${value}">${value}</option>`).join('');
}

function renderFirstRunNotice(exists) {
  const notice = $('firstRunNotice');
  if (exists) {
    notice.classList.add('hidden');
    notice.textContent = '';
    return;
  }
  notice.classList.remove('hidden');
  notice.textContent = 'First run: .env.stockfish does not exist yet. Start with defaults, then save your local settings.';
}

function renderStatusCards(readiness, lichess = null) {
  const host = $('statusCards');
  const template = $('statusTemplate');
  host.innerHTML = '';
  const entries = [
    ['Stockfish', readiness?.stockfish],
    ['Maia 2', readiness?.maia],
  ];
  if (lichess) entries.push(['Lichess', lichess]);
  for (const [name, data] of entries) {
    if (!data) continue;
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector('.status-name').textContent = name;
    const pill = node.querySelector('.status-pill');
    const status = data.status || (data.ok ? 'available' : 'unknown');
    pill.textContent = status;
    pill.classList.add(status);
    node.querySelector('.status-details').textContent = data.details || data.message || '';
    host.appendChild(node);
  }
}

function setOutputPaths(paths) {
  const host = $('outputPaths');
  host.innerHTML = '';
  for (const [label, value] of Object.entries(paths)) {
    if (!value) continue;
    const node = document.createElement('div');
    node.className = 'status-card';
    const title = document.createElement('strong');
    title.textContent = label;
    const body = document.createElement('div');
    body.textContent = value;
    node.append(title, body);
    host.appendChild(node);
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw data;
  }
  return data;
}

async function loadBootstrap() {
  const bootstrap = await api('/api/bootstrap');
  state.bootstrap = bootstrap;
  state.options = bootstrap.options || state.options;
  $('configPath').textContent = bootstrap.paths.config_path;
  populateSelects();
}

async function loadConfig() {
  const response = await api('/api/config');
  state.options = response.options || state.options;
  populateSelects();
  renderFirstRunNotice(response.exists);
  renderValidation(response.validation);
  fillForm(response.config);
}

async function saveConfig() {
  try {
    const response = await api('/api/config', {
      method: 'POST',
      body: JSON.stringify(currentConfigFromForm()),
    });
    renderValidation(response.validation || { ok: true, errors: {}, warnings: {} });
    appendLog(`Saved settings to ${response.path}`);
    renderFirstRunNotice(true);
  } catch (error) {
    renderValidation(error);
    appendLog('Save blocked: fix the highlighted settings first.');
  }
}

async function testReadiness() {
  state.readiness = await api('/api/readiness');
  renderStatusCards(state.readiness);
}

async function testLichess() {
  try {
    const result = await api('/api/lichess/test', {
      method: 'POST',
      body: JSON.stringify({ username: $('default_player').value.trim(), token: $('lichess_token').value }),
    });
    renderStatusCards(state.readiness, result);
    appendLog(result.message || 'Lichess test completed.');
  } catch (error) {
    renderStatusCards(state.readiness, error);
    appendLog(error.message || 'Lichess test failed.');
  }
}

async function importRecentGames() {
  try {
    const result = await api('/api/import-lichess', {
      method: 'POST',
      body: JSON.stringify({
        username: $('default_player').value.trim(),
        max_games: Number($('import_max_games').value),
        perf: $('import_perf').value || null,
        rated_only: $('import_rated_only').checked,
        since_days: $('import_since_days').value ? Number($('import_since_days').value) : null,
        out_path: $('import_out_path').value.trim(),
      }),
    });
    $('analyse_pgn_path').value = result.out_path;
    $('analyse_pgn_path').dataset.manual = 'true';
    appendLog(result.stdout || `Imported PGN: ${result.out_path}`);
  } catch (error) {
    appendLog(JSON.stringify(error.errors || error));
  }
}

async function analyseGames() {
  try {
    const result = await api('/api/analyse', {
      method: 'POST',
      body: JSON.stringify({
        username: $('default_player').value.trim(),
        pgn_path: $('analyse_pgn_path').value.trim(),
        out_path: $('analyse_out_path').value.trim(),
        mock: false,
      }),
    });
    $('export_json_path').value = result.json_path;
    $('export_json_path').dataset.manual = 'true';
    setOutputPaths({ 'Markdown report': result.markdown_path, 'Structured JSON': result.json_path });
    appendLog(result.stdout || 'Analysis complete.');
  } catch (error) {
    appendLog(JSON.stringify(error.errors || error));
  }
}

async function exportAnnotatedPgn() {
  try {
    const result = await api('/api/export-annotated-pgn', {
      method: 'POST',
      body: JSON.stringify({
        json_path: $('export_json_path').value.trim(),
        out_path: $('export_out_path').value.trim(),
        max_games: Number($('export_max_games').value),
        critical_only: $('export_critical_only').checked,
        include_all_moves: false,
      }),
    });
    setOutputPaths({
      'Markdown report': $('analyse_out_path').value.trim(),
      'Structured JSON': $('export_json_path').value.trim(),
      'Annotated PGN': result.out_path,
    });
    appendLog(result.stdout || `Annotated PGN: ${result.out_path}`);
  } catch (error) {
    appendLog(JSON.stringify(error.errors || error));
  }
}

async function createDiagnosticBundle() {
  try {
    const result = await api('/api/diagnostics', {
      method: 'POST',
      body: JSON.stringify({
        include_pgn: $('diagnosticIncludePgn').checked,
        include_report: $('diagnosticIncludeReport').checked,
        selected_paths: {
          pgn: $('analyse_pgn_path').value.trim(),
          report: $('analyse_out_path').value.trim(),
        },
        recent_logs: $('logOutput').textContent.split('\n').filter(Boolean),
      }),
    });
    appendLog(`Created diagnostic bundle at ${result.path}`);
  } catch (error) {
    appendLog(JSON.stringify(error.errors || error));
  }
}

function bindInputs() {
  for (const id of ['default_player', 'default_pgn', 'default_out', 'stockfish_depth', 'stockfish_time_limit', 'maia2_game_type', 'maia2_device', 'maia2_target_elo']) {
    $(id).addEventListener('input', syncWorkflowDefaults);
  }
  for (const id of ['import_out_path', 'analyse_pgn_path', 'analyse_out_path', 'export_json_path', 'export_out_path']) {
    $(id).addEventListener('input', () => {
      $(id).dataset.manual = 'true';
    });
  }
}

function bindButtons() {
  $('createDefaultsButton').addEventListener('click', () => {
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
    appendLog('Loaded default settings into the form. Save when ready.');
  });
  $('saveConfigButton').addEventListener('click', saveConfig);
  $('testReadinessButton').addEventListener('click', testReadiness);
  $('testLichessButton').addEventListener('click', testLichess);
  $('importGamesButton').addEventListener('click', importRecentGames);
  $('analyseGamesButton').addEventListener('click', analyseGames);
  $('exportPgnButton').addEventListener('click', exportAnnotatedPgn);
  $('diagnosticBundleButton').addEventListener('click', createDiagnosticBundle);
  $('clearLogButton').addEventListener('click', () => {
    $('logOutput').textContent = '';
  });
}

async function init() {
  bindInputs();
  bindButtons();
  await loadBootstrap();
  await loadConfig();
  await testReadiness();
}

init().catch((error) => {
  appendLog(`Fatal startup error: ${error.message || JSON.stringify(error)}`);
});
