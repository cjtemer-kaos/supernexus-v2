import { app, BrowserWindow, ipcMain } from "electron";
import * as path from "path";
import * as fs from "fs";

const NEXUS_BACKEND_URL = "http://127.0.0.1:9000";
const CONFIG_PATH = path.join(app.getPath("userData"), "nexus-config.json");

let mainWindow: BrowserWindow | null = null;
let avatarWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: "NEXUS IA - Director Avatar",
    frame: true,
    backgroundColor: "#0a0a0f",
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (process.env.NODE_ENV === "development") {
    mainWindow.loadURL("http://localhost:5173/");
  } else {
    mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }

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
    title: "NEXUS IA - Avatar",
    frame: true,
    backgroundColor: "#0a0a0f",
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  if (process.env.NODE_ENV === "development") {
    avatarWindow.loadURL("http://localhost:5173/avatar.html");
  } else {
    avatarWindow.loadFile(path.join(__dirname, "../renderer/avatar.html"));
  }

  avatarWindow.on("closed", () => {
    avatarWindow = null;
  });
}

ipcMain.handle("nexus:chat", async (_event, { message, gem, project, model, attachments, voice }: { message: string; gem?: string; project?: string; model?: string; attachments?: string[]; voice?: boolean }) => {
  try {
    const response = await fetch(`${NEXUS_BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, gem, project, model, attachments, voice }),
    });
    return await response.json();
  } catch (error) {
    return { error: "Backend not available", details: error };
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
    return { error: "Voice listen failed", details: error };
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
    return { error: "Voice speak failed", details: error };
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
    return { error: "Set personality failed", details: error };
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
    return { error: "Route failed", details: error };
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
    return { success: false, error };
  }
});

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  if (mainWindow === null) {
    createWindow();
  }
});
