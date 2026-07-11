const path = require('node:path');
const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron');

const { createNativeAffordances } = require('./native');
const { resolveRuntime, startDesktopServer } = require('./server');

const repoRoot = process.env.CHESS_COACH_PROJECT_ROOT || path.resolve(__dirname, '../../..');
let desktopServer = null;
let stopping = false;

function installNativeHandlers() {
  const native = createNativeAffordances({ repoRoot, dialog, shell });
  ipcMain.handle('chess-coach:pick-path', (_event, payload) => native.pickPath(payload));
  ipcMain.handle('chess-coach:open-path', (_event, target) => native.openPath(target));
  ipcMain.handle('chess-coach:open-external', (_event, url) => native.openExternal(url));
}

function isCanonicalLoopbackUrl(rawUrl) {
  try {
    return new URL(rawUrl).origin === new URL(desktopServer.url).origin;
  } catch {
    return false;
  }
}

function createWindow(server) {
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
      sandbox: true,
    },
  });
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event, url) => {
    if (!isCanonicalLoopbackUrl(url)) {
      event.preventDefault();
    }
  });
  window.loadURL(server.url);

  const smokeExitMs = Number(process.env.CHESS_COACH_DESKTOP_SMOKE_EXIT_MS || 0);
  if (smokeExitMs > 0) {
    window.webContents.once('did-finish-load', () => {
      console.log('Chess Coach desktop loaded the canonical React web root.');
      setTimeout(() => app.quit(), smokeExitMs);
    });
  }
}

async function stopDesktopServer() {
  if (!desktopServer || stopping) {
    return;
  }
  stopping = true;
  try {
    await desktopServer.stop();
  } finally {
    desktopServer = null;
    stopping = false;
  }
}

app.whenReady().then(async () => {
  installNativeHandlers();
  try {
    desktopServer = await startDesktopServer({ repoRoot, runtime: resolveRuntime({ cwd: repoRoot }) });
    createWindow(desktopServer);
  } catch {
    dialog.showErrorBox('Chess Coach could not start', 'The local Chess Coach server did not become ready. Check the local installation and retry.');
    app.quit();
    return;
  }
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0 && desktopServer) {
      createWindow(desktopServer);
    }
  });
});

app.on('before-quit', (event) => {
  if (!desktopServer || stopping) {
    return;
  }
  event.preventDefault();
  void stopDesktopServer().finally(() => app.quit());
});

app.on('window-all-closed', () => {
  app.quit();
});