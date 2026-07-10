const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('chessCoachDesktop', {
  pickPath: (payload) => ipcRenderer.invoke('chess-coach:pick-path', payload),
  openPath: (target) => ipcRenderer.invoke('chess-coach:open-path', target),
  openExternal: (url) => ipcRenderer.invoke('chess-coach:open-external', url),
});
