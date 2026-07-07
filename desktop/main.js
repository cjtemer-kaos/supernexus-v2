const { app, BrowserWindow, Tray, Menu, session, shell, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const http = require('http');

const SERVER_URL = 'http://localhost:9000/ui/';
const SERVER_API = 'http://localhost:9000/api/status';
let mainWindow = null;
let tray = null;
let serverProcess = null;

// ─── Server Management ──────────────────────────────────────────────────────
function serverRunning() {
  return new Promise((resolve) => {
    const req = http.get(SERVER_API, { timeout: 3000 }, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
  });
}

function startServer() {
  const projectDir = path.join(__dirname, '..');
  const pythonPath = process.env.PYTHON_PATH || 'C:\\Users\\cjtr\\AppData\\Local\\Programs\\Python\\Python313\\python.exe';
  serverProcess = spawn(pythonPath, ['start_server.py', '9000'], {
    cwd: projectDir,
    stdio: 'ignore',
    detached: false,
    windowsHide: true,
    shell: false,
  });
  serverProcess.unref();
}

// ─── Permission Handler ──────────────────────────────────────────────────────
function setupPermissions() {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowed = ['media', 'microphone', 'camera', 'notifications', 'display-capture'];
    callback(allowed.includes(permission));
  });
  session.defaultSession.setPermissionCheckHandler(() => true);
}

// ─── Zoom IPC Handlers ───────────────────────────────────────────────────────
function setupZoomHandlers() {
  ipcMain.handle('zoom-in', () => {
    if (!mainWindow) return 1;
    const level = mainWindow.webContents.getZoomLevel() + 0.5;
    mainWindow.webContents.setZoomLevel(level);
    return mainWindow.webContents.getZoomFactor();
  });

  ipcMain.handle('zoom-out', () => {
    if (!mainWindow) return 1;
    const level = mainWindow.webContents.getZoomLevel() - 0.5;
    mainWindow.webContents.setZoomLevel(level);
    return mainWindow.webContents.getZoomFactor();
  });

  ipcMain.handle('zoom-reset', () => {
    if (!mainWindow) return 1;
    mainWindow.webContents.setZoomLevel(0);
    mainWindow.webContents.setZoomFactor(1);
    return 1;
  });

  ipcMain.handle('zoom-get', () => {
    if (!mainWindow) return 1;
    return mainWindow.webContents.getZoomFactor();
  });
}

// ─── Keyboard Shortcuts ─────────────────────────────────────────────────────
function setupShortcuts() {
  // Ctrl++ = Zoom In
  mainWindow.webContents.on('before-input-event', (event, input) => {
    if (input.control && input.key === '=' && !input.shift && !input.alt) {
      event.preventDefault();
      const level = mainWindow.webContents.getZoomLevel() + 0.5;
      mainWindow.webContents.setZoomLevel(level);
      mainWindow.webContents.send('zoom-changed', mainWindow.webContents.getZoomFactor());
    }
    // Ctrl+- = Zoom Out
    if (input.control && input.key === '-' && !input.shift && !input.alt) {
      event.preventDefault();
      const level = mainWindow.webContents.getZoomLevel() - 0.5;
      mainWindow.webContents.setZoomLevel(level);
      mainWindow.webContents.send('zoom-changed', mainWindow.webContents.getZoomFactor());
    }
    // Ctrl+0 = Reset Zoom
    if (input.control && input.key === '0' && !input.shift && !input.alt) {
      event.preventDefault();
      mainWindow.webContents.setZoomLevel(0);
      mainWindow.webContents.setZoomFactor(1);
      mainWindow.webContents.send('zoom-changed', 1);
    }
  });
}

// ─── Window ──────────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 900,
    minHeight: 600,
    title: 'SuperNEXUS v2',
    icon: path.join(__dirname, 'icon.png'),
    backgroundColor: '#0a0a0f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false,
    },
    autoHideMenuBar: true,
  });

  mainWindow.loadURL(SERVER_URL);

  // Capture console errors from the page
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    if (level >= 2) { // warnings and errors
      console.log(`[PAGE ${level === 2 ? 'WARN' : 'ERROR'}] ${message} (${sourceId}:${line})`);
    }
  });

  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  // Retry on load failure (server not ready yet)
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDesc) => {
    console.log('[SuperNEXUS] Load failed:', errorCode, errorDesc, '- retrying in 3s...');
    setTimeout(() => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.loadURL(SERVER_URL);
      }
    }, 3000);
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  setupShortcuts();

  mainWindow.on('close', (event) => {
    if (!app.isQuitting) { event.preventDefault(); mainWindow.hide(); }
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ─── System Tray ─────────────────────────────────────────────────────────────
function createTray() {
  tray = new Tray(path.join(__dirname, 'icon.png'));
  tray.setToolTip('SuperNEXUS v2');
  const contextMenu = Menu.buildFromTemplate([
    { label: 'Mostrar', click: () => { mainWindow.show(); mainWindow.focus(); } },
    { label: 'Recargar', click: () => mainWindow.reload() },
    { type: 'separator' },
    { label: 'Salir', click: () => { app.isQuitting = true; app.quit(); } }
  ]);
  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => { mainWindow.show(); mainWindow.focus(); });
}

// ─── App Lifecycle ───────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  setupPermissions();
  setupZoomHandlers();

  // Wait for server to respond to HTTP (not just TCP)
  let serverReady = await serverRunning();
  if (!serverReady) {
    startServer();
    for (let i = 0; i < 30; i++) {
      await new Promise(r => setTimeout(r, 2000));
      serverReady = await serverRunning();
      if (serverReady) break;
    }
  }

  if (serverReady) {
    createWindow();
    createTray();
  } else {
    console.error('[SuperNEXUS] Server failed to start after 60s');
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
    else mainWindow.show();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => { app.isQuitting = true; });
