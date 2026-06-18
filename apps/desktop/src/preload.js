const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('chessCoachDesktop', {
  getBootstrap: () => ipcRenderer.invoke('chess-coach:get-bootstrap'),
  loadConfig: () => ipcRenderer.invoke('chess-coach:load-config'),
  saveConfig: (payload) => ipcRenderer.invoke('chess-coach:save-config', payload),
  validateConfig: (payload) => ipcRenderer.invoke('chess-coach:validate-config', payload),
  testReadiness: () => ipcRenderer.invoke('chess-coach:test-readiness'),
  testLichess: (payload) => ipcRenderer.invoke('chess-coach:test-lichess', payload),
  pickPath: (payload) => ipcRenderer.invoke('chess-coach:pick-path', payload),
  exportSettings: (payload) => ipcRenderer.invoke('chess-coach:export-settings', payload),
  previewSettingsImport: (payload) => ipcRenderer.invoke('chess-coach:preview-settings-import', payload),
  applyImportedSettings: (payload) => ipcRenderer.invoke('chess-coach:apply-imported-settings', payload),
  createDiagnosticBundle: (payload) => ipcRenderer.invoke('chess-coach:create-diagnostic-bundle', payload),
  openExternal: (url) => ipcRenderer.invoke('chess-coach:open-external', url),
  openPath: (target) => ipcRenderer.invoke('chess-coach:open-path', target),
  importLichess: (payload) => ipcRenderer.invoke('chess-coach:import-lichess', payload),
  analyseGames: (payload) => ipcRenderer.invoke('chess-coach:analyse-games', payload),
  exportAnnotatedPgn: (payload) => ipcRenderer.invoke('chess-coach:export-annotated-pgn', payload),
  getDefaultPaths: (username) => ipcRenderer.invoke('chess-coach:get-default-paths', username),
  onLog: (callback) => {
    const listener = (_event, entry) => callback(entry);
    ipcRenderer.on('chess-coach:log', listener);
    return () => ipcRenderer.removeListener('chess-coach:log', listener);
  },
});
