const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const {
  buildAnalyseArgs,
  buildExportAnnotatedArgs,
  buildGuiSupportArgs,
  buildImportLichessArgs,
  defaultAnnotatedPgnPath,
  defaultImportedPgnPath,
} = require('../src/common/commands');
const { buildLaunchPlan, hasGraphicalDisplay, needsNoSandbox } = require('../scripts/start');
const { validateConfigDraft, validateWorkflowInput } = require('../src/common/validation');

test('command builders return argument arrays with no shell interpolation', () => {
  const importArgs = buildImportLichessArgs({
    username: 'ExampleUser',
    maxGames: 20,
    perf: 'rapid',
    ratedOnly: true,
    sinceDays: 14,
    outPath: 'input/lichess_recent_ExampleUser.pgn',
  });
  assert.deepEqual(importArgs, [
    '-m',
    'chess_coach',
    'import-lichess',
    '--user',
    'ExampleUser',
    '--max',
    '20',
    '--out',
    'input/lichess_recent_ExampleUser.pgn',
    '--perf',
    'rapid',
    '--rated-only',
    '--since-days',
    '14',
  ]);
  assert.equal(importArgs.includes('ExampleUser && rm -rf /'), false);

  assert.deepEqual(buildAnalyseArgs({ username: 'ExampleUser', pgnPath: 'input/games.pgn', outPath: 'reports/latest.md' }), [
    '-m', 'chess_coach', 'analyse', '--pgn', 'input/games.pgn', '--out', 'reports/latest.md', '--player', 'ExampleUser', '--update-state',
  ]);

  assert.deepEqual(buildExportAnnotatedArgs({ jsonPath: 'reports/latest.json', outPath: 'reports/annotated/latest.pgn', maxGames: 10, criticalOnly: true }), [
    '-m', 'chess_coach', 'export-annotated-pgn', '--from', 'reports/latest.json', '--out', 'reports/annotated/latest.pgn', '--max-games', '10', '--critical-only',
  ]);

  assert.deepEqual(buildGuiSupportArgs('read-config', '/tmp/.env.stockfish'), ['-m', 'chess_coach.gui_support', 'read-config', '--env-file', '/tmp/.env.stockfish']);
  assert.deepEqual(buildGuiSupportArgs('render-config', null, ['--redact-token']), ['-m', 'chess_coach.gui_support', 'render-config', '--redact-token']);
});

test('renderer-side config validation catches invalid values and warns on unknown device', () => {
  const result = validateConfigDraft({
    default_player: 'bad name!',
    stockfish_depth: 0,
    stockfish_time_limit: 45,
    maia2_game_type: 'hyperbullet',
    maia2_device: 'gpu',
    maia2_target_elo: 999,
    default_pgn: '/tmp/games.pgn',
    default_out: '/tmp/report.md',
  }, { requireUsername: true });

  assert.equal(result.ok, false);
  assert.match(result.errors.default_player, /letters/);
  assert.match(result.errors.stockfish_depth, /1 to 30/);
  assert.match(result.errors.stockfish_time_limit, /0.01 to 30/);
  assert.match(result.errors.maia2_game_type, /rapid/);
  assert.match(result.errors.maia2_target_elo, /1100/);
  assert.match(result.warnings.maia2_device, /Unknown device/);
  assert.match(result.warnings.default_pgn, /Absolute path/);
  assert.match(result.warnings.default_out, /Absolute path/);
});

test('workflow validation rejects missing required inputs', () => {
  assert.equal(validateWorkflowInput('import', { username: '' }).ok, false);
  assert.equal(validateWorkflowInput('analyse', { username: 'ExampleUser', pgnPath: '', outPath: 'reports/latest.md' }).ok, false);
  assert.equal(validateWorkflowInput('export', { jsonPath: 'reports/latest.json', outPath: '', maxGames: 0 }).ok, false);
});

test('desktop main process is a secured thin shell over the canonical loopback web root', () => {
  const mainText = fs.readFileSync(path.join(__dirname, '..', 'src', 'main.js'), 'utf-8');
  const legacyRenderer = path.join(__dirname, '..', 'src', 'renderer', 'index.html');

  assert.equal(fs.existsSync(legacyRenderer), true, 'legacy renderer remains available for rollback');
  assert.match(mainText, /path\.resolve\(__dirname, '\.\.\/\.\.\/\.\.'\)/);
  assert.match(mainText, /startDesktopServer/);
  assert.match(mainText, /window\.loadURL\(server\.url\)/);
  assert.doesNotMatch(mainText, /loadFile\(/);
  assert.doesNotMatch(mainText, /chess-coach:(?:load-config|save-config|import-lichess|analyse-games|export-annotated-pgn|create-diagnostic-bundle)/);
  assert.match(mainText, /CHESS_COACH_DESKTOP_SMOKE_EXIT_MS/);
  assert.match(mainText, /contextIsolation:\s*true/);
  assert.match(mainText, /nodeIntegration:\s*false/);
  assert.match(mainText, /sandbox:\s*true/);
  assert.match(mainText, /setWindowOpenHandler/);
  assert.match(mainText, /will-navigate/);
  assert.match(mainText, /did-finish-load[\s\S]*canonical React web root/);
});

test('preload exposes only the three narrow native methods', () => {
  const preloadText = fs.readFileSync(path.join(__dirname, '..', 'src', 'preload.js'), 'utf-8');
  const calls = [];
  let bridge = null;
  const context = {
    require(name) {
      assert.equal(name, 'electron');
      return {
        contextBridge: { exposeInMainWorld(_name, value) { bridge = value; } },
        ipcRenderer: { invoke(channel, payload) { calls.push([channel, payload]); return Promise.resolve(); } },
      };
    },
  };

  vm.runInNewContext(preloadText, context, { filename: 'preload.js' });

  assert.deepEqual(Object.keys(bridge), ['pickPath', 'openPath', 'openExternal']);
  bridge.pickPath({ purpose: 'pgnInput' });
  bridge.openPath('reports/latest.md');
  bridge.openExternal('https://lichess.org/study');
  assert.deepEqual(calls, [
    ['chess-coach:pick-path', { purpose: 'pgnInput' }],
    ['chess-coach:open-path', 'reports/latest.md'],
    ['chess-coach:open-external', 'https://lichess.org/study'],
  ]);
});

test('classic renderer scripts load together and bind primary buttons', async () => {
  const srcRoot = path.join(__dirname, '..', 'src');
  const html = fs.readFileSync(path.join(srcRoot, 'renderer', 'index.html'), 'utf-8');
  const ids = [...html.matchAll(/id="([^"]+)"/g)].map((match) => match[1]);

  class FakeElement {
    constructor(id = '') {
      this.id = id;
      this.value = '';
      this.textContent = '';
      this.innerHTML = '';
      this.checked = false;
      this.dataset = {};
      this.listeners = {};
      this.children = [];
      this.classList = { add() {}, remove() {} };
      this.style = {};
      this.scrollHeight = 0;
      this.scrollTop = 0;
    }
    addEventListener(type, listener) { (this.listeners[type] ||= []).push(listener); }
    appendChild(child) { this.children.push(child); return child; }
    append(...children) { this.children.push(...children); }
    querySelector() { return new FakeElement(); }
    cloneNode() { return new FakeElement(`${this.id}-clone`); }
  }

  const elements = Object.fromEntries(ids.map((id) => [id, new FakeElement(id)]));
  elements.statusTemplate.content = { firstElementChild: new FakeElement('status-template-child') };
  const bridge = {
    getBootstrap: async () => ({ configPath: '/tmp/.env.stockfish' }),
    loadConfig: async () => ({
      exists: false,
      config: {
        default_player: '', lichess_token: '', default_pgn: 'input/sample_games.pgn', default_out: 'reports/latest.md',
        stockfish_path: '', stockfish_depth: 12, stockfish_time_limit: 0.1, maia2_enabled: false,
        maia2_game_type: 'rapid', maia2_device: 'cpu', maia2_target_elo: 1500,
      },
      validation: { ok: true, errors: {}, warnings: {} },
    }),
    testReadiness: async () => ({ stockfish: { status: 'not_configured' }, maia: { status: 'disabled' } }),
    onLog: () => {},
  };
  const context = {
    window: { chessCoachDesktop: bridge, confirm: () => false },
    document: {
      getElementById(id) { return elements[id] ||= new FakeElement(id); },
      createElement(tag) { return new FakeElement(tag); },
      querySelectorAll() { return []; },
    },
    console,
    setTimeout,
    clearTimeout,
  };
  vm.createContext(context);

  for (const rel of ['common/validation.js', 'common/commands.js', 'renderer/app.js']) {
    vm.runInContext(fs.readFileSync(path.join(srcRoot, rel), 'utf-8'), context, { filename: rel });
  }
  await new Promise((resolve) => setTimeout(resolve, 25));

  for (const id of ['saveConfigButton', 'createDefaultsButton', 'resetDefaultsButton', 'testReadinessButton', 'testLichessButton', 'importGamesButton', 'analyseGamesButton', 'exportPgnButton']) {
    assert.equal(elements[id].listeners.click?.length, 1, `${id} should have exactly one click listener`);
  }
});

test('default output helpers derive stable local-first paths', () => {
  assert.equal(defaultImportedPgnPath('ExampleUser'), 'input/lichess_recent_ExampleUser.pgn');
  assert.equal(defaultAnnotatedPgnPath('ExampleUser'), 'reports/annotated/ExampleUser_annotated.pgn');
});

test('desktop start preflight reports whether a graphical display is available', () => {
  assert.equal(hasGraphicalDisplay({ DISPLAY: ':0' }), true);
  assert.equal(hasGraphicalDisplay({ WAYLAND_DISPLAY: 'wayland-0' }), true);
  assert.equal(hasGraphicalDisplay({}), false);
});

test('desktop start preflight adds --no-sandbox only for Linux helper permission mismatch', () => {
  assert.equal(needsNoSandbox({ platform: 'linux', chromeSandboxStat: { uid: 1000, mode: 0o100755 } }), true);
  assert.equal(needsNoSandbox({ platform: 'linux', chromeSandboxStat: { uid: 0, mode: 0o104755 } }), false);
  assert.equal(needsNoSandbox({ platform: 'darwin', chromeSandboxStat: { uid: 1000, mode: 0o100755 } }), false);

  const plan = buildLaunchPlan({
    platform: 'linux',
    env: { DISPLAY: ':0' },
    electronPath: '/tmp/electron',
    guiAppPath: '/tmp/main.js',
    chromeSandboxStat: { uid: 1000, mode: 0o100755 },
  });

  assert.deepEqual(plan.args, ['--no-sandbox', '/tmp/main.js']);
  assert.match(plan.warnings[0], /--no-sandbox/);
  assert.deepEqual(plan.errors, []);
});

test('desktop start preflight blocks headless Linux launches with a clear error', () => {
  const plan = buildLaunchPlan({
    platform: 'linux',
    env: {},
    electronPath: '/tmp/electron',
    guiAppPath: '/tmp/main.js',
    chromeSandboxStat: null,
  });

  assert.deepEqual(plan.args, ['/tmp/main.js']);
  assert.match(plan.errors[0], /No graphical display detected/);
});
