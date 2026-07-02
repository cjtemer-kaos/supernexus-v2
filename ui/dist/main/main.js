"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const child_process_1 = require("child_process");
const NEXUS_BACKEND_URL = "http://127.0.0.1:9000";
const CONFIG_PATH = path.join(electron_1.app.getPath("userData"), "nexus-config.json");
const isDev = process.env.NODE_ENV === "development" || process.env.DEBUG === "true";
let mainWindow = null;
let avatarWindow = null;
let backendProcess = null;
let tray = null;
function getProjectRoot() {
    return "D:\\ias\\proyectos\\supernexus-v2";
}
const NEXUS_PORT = 9000;
async function isPortInUse(port) {
    try {
        const res = await fetch(`http://127.0.0.1:${port}/api/status`, { signal: AbortSignal.timeout(2000) });
        return res.ok;
    }
    catch {
        return false;
    }
}
function startBackend() {
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
        const proc = (0, child_process_1.spawn)(python, [serverScript, String(NEXUS_PORT)], {
            cwd: root,
            env,
            stdio: ["ignore", "pipe", "pipe"],
            windowsHide: true,
            ...(process.platform === "win32" ? { creationFlags: 0x08000000 } : {}),
        });
        backendProcess = proc;
        proc.stdout?.on("data", (data) => {
            console.log(`[backend] ${data.toString().trim()}`);
        });
        proc.stderr?.on("data", (data) => {
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
            }
            catch { }
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
    mainWindow = new electron_1.BrowserWindow({
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
    }
    else {
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
    avatarWindow = new electron_1.BrowserWindow({
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
    }
    else {
        avatarWindow.loadFile(path.join(__dirname, "../avatar.html"));
    }
    avatarWindow.on("closed", () => {
        avatarWindow = null;
    });
}
function createTray() {
    const iconSize = 16;
    const icon = electron_1.nativeImage.createEmpty();
    tray = new electron_1.Tray(icon);
    tray.setToolTip("SuperNEXUS v2");
    const contextMenu = electron_1.Menu.buildFromTemplate([
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
                    const data = await res.json();
                    electron_1.dialog.showMessageBox({
                        type: "info",
                        title: "SuperNEXUS - Estado",
                        message: `Servidor: ${data.online ? "🟢 Online" : "🔴 Offline"}`,
                        detail: JSON.stringify(data, null, 2),
                    });
                }
                catch {
                    electron_1.dialog.showMessageBox({
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
                electron_1.app.quit();
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
            (0, child_process_1.spawn)("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"]);
        }
        else {
            backendProcess.kill("SIGTERM");
        }
        backendProcess = null;
    }
}
// IPC handlers
electron_1.ipcMain.handle("nexus:chat", async (_event, { message, gem, project, model, attachments, voice }) => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, gem, project, model, attachments, voice }),
        });
        return await response.json();
    }
    catch (error) {
        return { error: "Backend not available", details: String(error) };
    }
});
electron_1.ipcMain.handle("nexus:status", async () => {
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
    }
    catch (error) {
        console.error("Status check failed:", error);
        return { online: false };
    }
});
electron_1.ipcMain.handle("nexus:projects", async () => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/projects`);
        return await response.json();
    }
    catch {
        return { projects: [] };
    }
});
electron_1.ipcMain.handle("nexus:gems", async () => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/gems`);
        return await response.json();
    }
    catch {
        return { gems: [] };
    }
});
electron_1.ipcMain.handle("nexus:memory:search", async (_event, query) => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/memory/search`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
        });
        return await response.json();
    }
    catch {
        return { results: [] };
    }
});
electron_1.ipcMain.handle("nexus:knowledge:graph", async () => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/knowledge/graph`);
        return await response.json();
    }
    catch {
        return { nodes: [], edges: [] };
    }
});
electron_1.ipcMain.handle("nexus:tailscale:nodes", async () => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/tailscale/nodes`);
        return await response.json();
    }
    catch {
        return { nodes: [] };
    }
});
electron_1.ipcMain.handle("nexus:open-avatar", () => {
    createAvatarWindow();
});
electron_1.ipcMain.handle("nexus:system-stats", async () => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/system/stats`);
        return await response.json();
    }
    catch {
        return { cpu: 0, memory: 0, gpu: 0, disk: 0 };
    }
});
electron_1.ipcMain.handle("nexus:voice:listen", async (_event, { timeout }) => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/listen?timeout=${timeout || 5}`);
        return await response.json();
    }
    catch (error) {
        return { error: "Voice listen failed", details: String(error) };
    }
});
electron_1.ipcMain.handle("nexus:voice:speak", async (_event, { text }) => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/speak`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text }),
        });
        return await response.json();
    }
    catch (error) {
        return { error: "Voice speak failed", details: String(error) };
    }
});
electron_1.ipcMain.handle("nexus:voice:status", async () => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/status`);
        return await response.json();
    }
    catch {
        return { audio_ready: false, model_loaded: false };
    }
});
electron_1.ipcMain.handle("nexus:voice:personalities", async () => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/personalities`);
        return await response.json();
    }
    catch {
        return { personalities: [], current: "director" };
    }
});
electron_1.ipcMain.handle("nexus:voice:set-personality", async (_event, { personality }) => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/set-personality`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ personality }),
        });
        return await response.json();
    }
    catch (error) {
        return { error: "Set personality failed", details: String(error) };
    }
});
electron_1.ipcMain.handle("nexus:voice:route", async (_event, { query }) => {
    try {
        const response = await fetch(`${NEXUS_BACKEND_URL}/api/voice/route`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
        });
        return await response.json();
    }
    catch (error) {
        return { error: "Route failed", details: String(error) };
    }
});
electron_1.ipcMain.handle("nexus:get-config", async () => {
    try {
        if (fs.existsSync(CONFIG_PATH)) {
            const data = fs.readFileSync(CONFIG_PATH, "utf-8");
            return JSON.parse(data);
        }
        return null;
    }
    catch {
        return null;
    }
});
electron_1.ipcMain.handle("nexus:set-config", async (_event, config) => {
    try {
        const dir = path.dirname(CONFIG_PATH);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
        return { success: true };
    }
    catch (error) {
        return { success: false, error: String(error) };
    }
});
electron_1.ipcMain.handle("nexus:backend:restart", async () => {
    cleanupBackend();
    try {
        await startBackend();
        return { success: true };
    }
    catch (error) {
        return { success: false, error: String(error) };
    }
});
electron_1.ipcMain.handle("nexus:backend:status", () => {
    return { running: backendProcess !== null && backendProcess.exitCode === null };
});
// Zoom IPC
let zoomFactor = 1.0;
electron_1.ipcMain.handle("nexus:zoom:get", () => zoomFactor);
electron_1.ipcMain.handle("nexus:zoom:set", (_event, factor) => {
    zoomFactor = Math.max(0.5, Math.min(2.0, factor));
    mainWindow?.webContents.setZoomFactor(zoomFactor);
    return zoomFactor;
});
electron_1.ipcMain.handle("nexus:zoom:in", () => {
    zoomFactor = Math.min(2.0, zoomFactor + 0.1);
    mainWindow?.webContents.setZoomFactor(zoomFactor);
    return zoomFactor;
});
electron_1.ipcMain.handle("nexus:zoom:out", () => {
    zoomFactor = Math.max(0.5, zoomFactor - 0.1);
    mainWindow?.webContents.setZoomFactor(zoomFactor);
    return zoomFactor;
});
electron_1.ipcMain.handle("nexus:zoom:reset", () => {
    zoomFactor = 1.0;
    mainWindow?.webContents.setZoomFactor(zoomFactor);
    return zoomFactor;
});
electron_1.app.whenReady().then(async () => {
    createTray();
    try {
        await startBackend();
    }
    catch (err) {
        console.error("Backend startup failed:", err);
        electron_1.dialog.showErrorBox("Error del servidor", `No se pudo iniciar el backend de SuperNEXUS.\n\n${err}`);
    }
    createWindow();
});
electron_1.app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        cleanupBackend();
        electron_1.app.quit();
    }
});
electron_1.app.on("activate", () => {
    if (mainWindow === null) {
        createWindow();
    }
});
electron_1.app.on("before-quit", () => {
    cleanupBackend();
    tray?.destroy();
    tray = null;
});
//# sourceMappingURL=main.js.map