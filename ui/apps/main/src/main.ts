import { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, dialog } from "electron";
import * as path from "path";
import * as fs from "fs";
import { spawn, ChildProcess } from "child_process";

const NEXUS_BACKEND_URL = "http://127.0.0.1:9000";
const CONFIG_PATH = path.join(app.getPath("userData"), "nexus-config.json");
const isDev = process.env.NODE_ENV === "development" || process.env.DEBUG === "true";

let mainWindow: BrowserWindow | null = null;
let avatarWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;
let tray: Tray | null = null;

function getProjectRoot(): string {
  return "D:\\ias\\proyectos\\supernexus-v2";
}

const NEXUS_PORT = 9000;

async function isPortInUse(port: number): Promise<boolean> {
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/status`, { signal: AbortSignal.timeout(2000) });
    return res.ok;
  } catch {
    return false;
  }
}

function startBackend(): Promise<void> {
  return new Promise(async (resolve, reject) => {
    if (await isPortInUse(NEXUS_PORT)) {
      console.log(`Port ${NEXUS_PORT} already in use — reusing existing backend`);
      resolve();
      return;
    }

    const root = getProjectRoot();
    const python = "python";
    const serverScript = path.join(root, "src", "api", "server.py");

    if (!fs.existsSync(serverScript)) {
      reject(new Error(`Server script not found: ${serverScript}`));
      return;
    }

    const env = {
      ...process.env,
      NEXUS_BRAIN: path.join(root, "brain"),
      PYTHONPATH: root,
      PYTHONDONTWRITEBYTECODE: "1",
    };

    const proc = spawn(python, [serverScript, String(NEXUS_PORT)], {
      cwd: root,
      env,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
      ...(process.platform === "win32" ? { creationFlags: 0x08000000 } : {}),
    } as any);
    backendProcess = proc;

    proc.stdout?.on("data", (data: Buffer) => {
      console.log(`[backend] ${data.toString().trim()}`);
    });

    proc.stderr?.on("data", (data: Buffer) => {
      console.error(`[backend] ${data.toString().trim()}`);
    });

    proc.on("error", (err) => {
      console.error("Failed to start backend:", err);
      reject(err);
    });

    proc.on("exit", (code) => {
      console.log(`Backend exited with code ${code}`);
      backendProcess = null;
    });

    let attempts = 0;
    const maxAttempts = 30;
    const ping = async () => {
      attempts++;
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 2000);
        const res = await fetch(`${NEXUS_BACKEND_URL}/api/status`, { signal: controller.signal });
        clearTimeout(timeout);
        if (res.ok) {
          console.log("Backend ready after", attempts, "attempts");
          resolve();
          return;
        }
      } catch {}
      if (attempts >= maxAttempts) {
        reject(new Error("Backend did not start in time"));
        return;
      }
      setTimeout(ping, 1000);
    };
    setTimeout(ping, 1500);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: "SuperNEXUS v2",
    frame: true,
    backgroundColor: "#0a0a0f",
    icon: path.join(__dirname, "..", "..", "public", "favicon.svg"),
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173/");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../index.html"));
  }

  mainWindow.on("close", (event) => {
    if (tray) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function createAvatarWindow() {
  if (avatarWindow && !avatarWindow.isDestroyed()) {
    avatarWindow.focus();
    return;
  }

  avatarWindow = new BrowserWindow({
    width: 500,
    height: 600,
    minWidth: 400,
    minHeight: 500,
    title: "SuperNEXUS - Avatar",
    frame: true,
    backgroundColor: "#0a0a0f",
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (isDev) {
    avatarWindow.loadURL("http://localhost:5173/avatar.html");
  } else {
    avatarWindow.loadFile(path.join(__dirname, "../avatar.html"));
  }

  avatarWindow.on("closed", () => {
    avatarWindow = null;
  });
}

function createTray() {
  const iconSize = 16;
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);
  tray.setToolTip("SuperNEXUS v2");

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Abrir SuperNEXUS",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    { type: "separator" },
    {
      label: "Estado del servidor",
      click: async () => {
        try {
          const res = await fetch(`${NEXUS_BACKEND_URL}/api/status`);
          const data = await res.json() as Record<string, unknown>;
          dialog.showMessageBox({
            type: "info",
            title: "SuperNEXUS - Estado",
            message: `Servidor: ${data.online ? "🟢 Online" : "🔴 Offline"}`,
            detail: JSON.stringify(data, null, 2),
          });
        } catch {
          dialog.showMessageBox({
            type: "error",
            title: "SuperNEXUS - Estado",
            message: "Servidor no disponible",
          });
        }
      },
    },
    { type: "separator" },
    {
      label: "Salir",
      click: () => {
        tray?.destroy();
        tray = null;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);
  tray.on("double-click", () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function cleanupBackend() {
  if (backendProcess) {
    console.log("Stopping backend...");
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"]);
    } else {
      backendProcess.kill("SIGTERM");
    }
    backendProcess = null;
  }
}

// IPC handlers
ipcMain.handle("nexus:chat", async (_event, { message, gem, project, model, attachments, voice }: { message: string; gem?: string; project?: string; model?: string; attachments?: string[]; voice?: boolean }) => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, gem, project, model, attachments, voice }),
    });
    return await response.json();
  } catch (error) {
    return { error: "Backend not available", details: String(error) };
  }
});

ipcMain.handle("nexus:status", async () => {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/status`, { signal: controller.signal });
    clearTimeout(timeoutId);
    if (response.ok) {
      const data = await response.json();
      return data && typeof data === 'object' ? { ...data, online: true } : { online: true };
    }
    return { online: false };
  } catch (error) {
    console.error("Status check failed:", error);
    return { online: false };
  }
});

ipcMain.handle("nexus:projects", async () => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/projects`);
    return await response.json();
  } catch {
    return { projects: [] };
  }
});

ipcMain.handle("nexus:gems", async () => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/gems`);
    return await response.json();
  } catch {
    return { gems: [] };
  }
});

ipcMain.handle("nexus:memory:search", async (_event, query: string) => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/memory/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    return await response.json();
  } catch {
    return { results: [] };
  }
});

ipcMain.handle("nexus:knowledge:graph", async () => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/knowledge/graph`);
    return await response.json();
  } catch {
    return { nodes: [], edges: [] };
  }
});

ipcMain.handle("nexus:tailscale:nodes", async () => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/tailscale/nodes`);
    return await response.json();
  } catch {
    return { nodes: [] };
  }
});

ipcMain.handle("nexus:open-avatar", () => {
  createAvatarWindow();
});

ipcMain.handle("nexus:system-stats", async () => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/system/stats`);
    return await response.json();
  } catch {
    return { cpu: 0, memory: 0, gpu: 0, disk: 0 };
  }
});

ipcMain.handle("nexus:voice:listen", async (_event, { timeout }: { timeout?: number }) => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/listen?timeout=${timeout || 5}`);
    return await response.json();
  } catch (error) {
    return { error: "Voice listen failed", details: String(error) };
  }
});

ipcMain.handle("nexus:voice:speak", async (_event, { text }: { text: string }) => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    return await response.json();
  } catch (error) {
    return { error: "Voice speak failed", details: String(error) };
  }
});

ipcMain.handle("nexus:voice:status", async () => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/status`);
    return await response.json();
  } catch {
    return { audio_ready: false, model_loaded: false };
  }
});

ipcMain.handle("nexus:voice:personalities", async () => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/personalities`);
    return await response.json();
  } catch {
    return { personalities: [], current: "director" };
  }
});

ipcMain.handle("nexus:voice:set-personality", async (_event, { personality }: { personality: string }) => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/set-personality`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ personality }),
    });
    return await response.json();
  } catch (error) {
    return { error: "Set personality failed", details: String(error) };
  }
});

ipcMain.handle("nexus:voice:route", async (_event, { query }: { query: string }) => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    return await response.json();
  } catch (error) {
    return { error: "Route failed", details: String(error) };
  }
});

ipcMain.handle("nexus:get-config", async () => {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const data = fs.readFileSync(CONFIG_PATH, "utf-8");
      return JSON.parse(data);
    }
    return null;
  } catch {
    return null;
  }
});

ipcMain.handle("nexus:set-config", async (_event, config: any) => {
  try {
    const dir = path.dirname(CONFIG_PATH);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
    return { success: true };
  } catch (error) {
    return { success: false, error: String(error) };
  }
});

ipcMain.handle("nexus:backend:restart", async () => {
  cleanupBackend();
  try {
    await startBackend();
    return { success: true };
  } catch (error) {
    return { success: false, error: String(error) };
  }
});

ipcMain.handle("nexus:backend:status", () => {
  return { running: backendProcess !== null && backendProcess.exitCode === null };
});

app.whenReady().then(async () => {
  createTray();

  try {
    await startBackend();
  } catch (err) {
    console.error("Backend startup failed:", err);
    dialog.showErrorBox("Error del servidor", `No se pudo iniciar el backend de SuperNEXUS.\n\n${err}`);
  }

  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    cleanupBackend();
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on("before-quit", () => {
  cleanupBackend();
  tray?.destroy();
  tray = null;
});
