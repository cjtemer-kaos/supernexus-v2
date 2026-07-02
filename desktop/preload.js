const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  isElectron: true,
  zoomIn: () => ipcRenderer.invoke('zoom-in'),
  zoomOut: () => ipcRenderer.invoke('zoom-out'),
  zoomReset: () => ipcRenderer.invoke('zoom-reset'),
  zoomGet: () => ipcRenderer.invoke('zoom-get'),
  onZoomChanged: (callback) => ipcRenderer.on('zoom-changed', (_, level) => callback(level)),
});
