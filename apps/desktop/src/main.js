const path = require('node:path');
const fs = require('node:fs');
const { spawn, spawnSync } = require('node:child_process');
const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');
const { MAIA_DEVICE_OPTIONS, MAIA_ELO_OPTIONS, MAIA_GAME_TYPE_OPTIONS, validateWorkflowInput } = require('./common/validation');
const {
  buildAnalyseArgs,
  buildExportAnnotatedArgs,
  buildGuiSupportArgs,
  buildImportLichessArgs,
  defaultAnnotatedPgnPath,
  defaultImportedPgnPath,
} = require('./common/commands');

const repoRoot = process.env.CHESS_COACH_PROJECT_ROOT || path.resolve(__dirname, '../../..');
const envFile = path.join(repoRoot, '.env.stockfish');
const explicitPython = process.env.CHESS_COACH_PYTHON || null;

function commandExists(command, args = ['--version']) {
  const probe = spawnSync(command, args, { cwd: repoRoot, stdio: 'ignore' });
  return probe.status === 0;
}

function resolveRuntime() {
  if (explicitPython) {
    return { executable: explicitPython, prefixArgs: [], description: explicitPython };
  }
  if (commandExists('uv')) {
    return { executable: 'uv', prefixArgs: ['run', 'python'], description: 'uv run python' };
  }
  if (commandExists('python')) {
    return { executable: 'python', prefixArgs: [], description: 'python' };
  }
  if (commandExists('python3')) {
    return { executable: 'python3', prefixArgs: [], description: 'python3' };
  }
  return { executable: 'python', prefixArgs: [], description: 'python' };
}

const runtime = resolveRuntime();
const windowLogHistory = [];
const MAX_LOG_LINES = 400;

function pushLog(entry) {
  const normalised = {
    timestamp: new Date().toISOString(),
    ...entry,
  };
  windowLogHistory.push(normalised);
  if (windowLogHistory.length > MAX_LOG_LINES) {
    windowLogHistory.splice(0, windowLogHistory.length - MAX_LOG_LINES);
  }
  for (const win of BrowserWindow.getAllWindows()) {
    win.webContents.send('chess-coach:log', normalised);
  }
}

function redactText(text, secrets = []) {
  let redacted = text;
  for (const secret of secrets) {
    if (secret) {
      redacted = redacted.split(secret).join('[redacted]');
    }
  }
  return redacted;
}

function runProcess(label, args, { stdinJson = null, secrets = [] } = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(runtime.executable, [...runtime.prefixArgs, ...args], {
      cwd: repoRoot,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: false,
    });
    let stdout = '';
    let stderr = '';
    pushLog({ level: 'info', label, message: `Started ${label}` });
    child.stdout.on('data', (chunk) => {
      const text = redactText(String(chunk), secrets);
      stdout += text;
      pushLog({ level: 'stdout', label, message: text });
    });
    child.stderr.on('data', (chunk) => {
      const text = redactText(String(chunk), secrets);
      stderr += text;
      pushLog({ level: 'stderr', label, message: text });
    });
    child.on('error', (error) => {
      reject(error);
    });
    child.on('close', (code) => {
      pushLog({
        level: code === 0 ? 'info' : 'error',
        label,
        message: code === 0 ? `${label} finished.` : `${label} failed with exit code ${code}.`,
      });
      resolve({ code, stdout, stderr });
    });
    if (stdinJson !== null) {
      child.stdin.write(JSON.stringify(stdinJson));
    }
    child.stdin.end();
  });
}

async function runJsonAction(label, action, actionArgs = [], stdinJson = null, secrets = [], { includeEnvFile = true } = {}) {
  const { code, stdout, stderr } = await runProcess(label, buildGuiSupportArgs(action, includeEnvFile ? envFile : null, actionArgs), { stdinJson, secrets });
  if (code !== 0) {
    throw new Error(stderr.trim() || `${label} failed with exit code ${code}`);
  }
  try {
    return JSON.parse(stdout || '{}');
  } catch (error) {
    throw new Error(`${label} returned invalid JSON: ${error.message}`);
  }
}

function defaultWindowState() {
  return {
    configPath: envFile,
    repoRoot,
    pythonExecutable: runtime.description,
    options: {
      maiaGameTypes: [...MAIA_GAME_TYPE_OPTIONS],
      maiaDevices: [...MAIA_DEVICE_OPTIONS],
      maiaElo: [...MAIA_ELO_OPTIONS],
    },
  };
}

async function pickPath(purpose, currentValue = '') {
  const common = { defaultPath: currentValue ? path.join(repoRoot, currentValue) : repoRoot };
  if (purpose === 'pgnInput' || purpose === 'settingsImport') {
    const result = await dialog.showOpenDialog({
      ...common,
      properties: ['openFile'],
      filters: purpose === 'settingsImport' ? [{ name: 'Environment files', extensions: ['env', 'stockfish', 'txt'] }] : [{ name: 'PGN files', extensions: ['pgn'] }],
    });
    return result.canceled ? null : result.filePaths[0];
  }
  const filtersByPurpose = {
    markdownOutput: [{ name: 'Markdown', extensions: ['md'] }],
    pgnOutput: [{ name: 'PGN', extensions: ['pgn'] }],
    settingsExport: [{ name: 'Environment files', extensions: ['env', 'stockfish', 'txt'] }],
  };
  const result = await dialog.showSaveDialog({
    ...common,
    filters: filtersByPurpose[purpose] || [],
  });
  return result.canceled ? null : result.filePath;
}

function relativeToRepo(filePath) {
  if (!filePath) {
    return filePath;
  }
  if (path.isAbsolute(filePath)) {
    const relative = path.relative(repoRoot, filePath);
    return !relative.startsWith('..') ? relative : filePath;
  }
  return filePath;
}

function isInsideRepo(target) {
  const resolved = path.resolve(repoRoot, target || '.');
  const relative = path.relative(repoRoot, resolved);
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function normaliseRepoPath(target) {
  if (!target) {
    throw new Error('Path is required.');
  }
  const resolved = path.isAbsolute(target) ? path.resolve(target) : path.resolve(repoRoot, target);
  if (!isInsideRepo(resolved)) {
    throw new Error('Only project-local paths can be opened from Chess Coach.');
  }
  return resolved;
}

function assertAllowedExternalUrl(rawUrl) {
  const allowedHosts = new Set(['lichess.org', 'stockfishchess.org']);
  let parsed;
  try {
    parsed = new URL(rawUrl);
  } catch {
    throw new Error('Invalid external URL.');
  }
  if (parsed.protocol !== 'https:' || !allowedHosts.has(parsed.hostname)) {
    throw new Error('External link blocked by Chess Coach allowlist.');
  }
  return parsed.toString();
}

function installHandlers() {
  ipcMain.handle('chess-coach:get-bootstrap', async () => defaultWindowState());
  ipcMain.handle('chess-coach:load-config', async () => runJsonAction('Load config', 'read-config'));
  ipcMain.handle('chess-coach:save-config', async (_event, payload) => runJsonAction('Save config', 'write-config', [], payload, [payload.lichess_token || '']));
  ipcMain.handle('chess-coach:validate-config', async (_event, payload) => runJsonAction('Validate config', 'validate-config', [], payload, [payload.lichess_token || ''], { includeEnvFile: false }));
  ipcMain.handle('chess-coach:test-readiness', async () => runJsonAction('Test readiness', 'test-readiness'));
  ipcMain.handle('chess-coach:test-lichess', async (_event, payload) =>
    runJsonAction('Test Lichess', 'test-lichess', ['--user', payload.username], { token: payload.token || '' }, [payload.token || ''], { includeEnvFile: false })
  );
  ipcMain.handle('chess-coach:pick-path', async (_event, payload) => {
    const selected = await pickPath(payload.purpose, payload.currentValue || '');
    return selected ? relativeToRepo(selected) : null;
  });
  ipcMain.handle('chess-coach:export-settings', async (_event, payload) => {
    const rendered = await runJsonAction('Render settings export', 'render-config', payload.redactToken ? ['--redact-token'] : [], payload.config, [payload.config.lichess_token || ''], { includeEnvFile: false });
    if (!rendered.ok) {
      return rendered;
    }
    const targetPath = payload.targetPath || (await pickPath('settingsExport', '.env.stockfish.export'));
    if (!targetPath) {
      return { ok: false, cancelled: true };
    }
    fs.writeFileSync(targetPath, rendered.text, 'utf-8');
    return { ok: true, path: targetPath };
  });
  ipcMain.handle('chess-coach:preview-settings-import', async (_event, payload) => {
    const sourcePath = payload.sourcePath || (await pickPath('settingsImport'));
    if (!sourcePath) {
      return { ok: false, cancelled: true };
    }
    const preview = await runJsonAction('Preview imported settings', 'preview-config-file', ['--env-file', sourcePath], null, [], { includeEnvFile: false });
    return { ok: true, sourcePath, preview };
  });
  ipcMain.handle('chess-coach:apply-imported-settings', async (_event, payload) => runJsonAction('Apply imported settings', 'write-config', [], payload.config, [payload.config.lichess_token || '']));
  ipcMain.handle('chess-coach:create-diagnostic-bundle', async (_event, payload) =>
    runJsonAction('Create diagnostic bundle', 'create-diagnostic-bundle', ['--project-root', repoRoot], {
      readiness: payload.readiness,
      recent_logs: windowLogHistory.map((entry) => `[${entry.timestamp}] ${entry.label || 'app'} ${entry.message}`),
      electron_context: {
        platform: process.platform,
        arch: process.arch,
        versions: process.versions,
      },
      include_pgn: payload.includePgn,
      include_report: payload.includeReport,
      selected_paths: payload.selectedPaths,
    }, [payload.token || ''])
  );
  ipcMain.handle('chess-coach:open-external', async (_event, url) => shell.openExternal(assertAllowedExternalUrl(url)));
  ipcMain.handle('chess-coach:open-path', async (_event, target) => shell.openPath(normaliseRepoPath(target)));
  ipcMain.handle('chess-coach:import-lichess', async (_event, payload) => {
    const validation = validateWorkflowInput('import', payload);
    if (!validation.ok) {
      return { ok: false, validation };
    }
    const result = await runProcess('Import recent games', buildImportLichessArgs(payload), {});
    return { ok: result.code === 0, exitCode: result.code, stdout: result.stdout, stderr: result.stderr, outPath: payload.outPath };
  });
  ipcMain.handle('chess-coach:analyse-games', async (_event, payload) => {
    const validation = validateWorkflowInput('analyse', payload);
    if (!validation.ok) {
      return { ok: false, validation };
    }
    const result = await runProcess('Analyse games', buildAnalyseArgs(payload), {});
    return {
      ok: result.code === 0,
      exitCode: result.code,
      stdout: result.stdout,
      stderr: result.stderr,
      markdownPath: payload.outPath,
      jsonPath: payload.outPath.replace(/\.md$/i, '.json'),
    };
  });
  ipcMain.handle('chess-coach:export-annotated-pgn', async (_event, payload) => {
    const validation = validateWorkflowInput('export', payload);
    if (!validation.ok) {
      return { ok: false, validation };
    }
    const result = await runProcess('Export annotated PGN', buildExportAnnotatedArgs(payload), {});
    return { ok: result.code === 0, exitCode: result.code, stdout: result.stdout, stderr: result.stderr, outPath: payload.outPath };
  });
  ipcMain.handle('chess-coach:get-default-paths', async (_event, username) => ({
    importedPgn: defaultImportedPgnPath(username),
    annotatedPgn: defaultAnnotatedPgnPath(username),
  }));
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1380,
    height: 920,
    backgroundColor: '#f7f6f2',
    autoHideMenuBar: true,
    title: 'Chess Coach',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  window.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  const smokeExitMs = Number(process.env.CHESS_COACH_DESKTOP_SMOKE_EXIT_MS || 0);
  if (smokeExitMs > 0) {
    window.webContents.once('did-finish-load', () => {
      setTimeout(() => app.quit(), smokeExitMs);
    });
  }
}

app.whenReady().then(() => {
  installHandlers();
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
