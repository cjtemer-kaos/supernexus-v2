"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld("nexusAPI", {
    chat: (message, gem, project, model, attachments, voice) => electron_1.ipcRenderer.invoke("nexus:chat", { message, gem, project, model, attachments, voice }),
    status: () => electron_1.ipcRenderer.invoke("nexus:status"),
    projects: () => electron_1.ipcRenderer.invoke("nexus:projects"),
    gems: () => electron_1.ipcRenderer.invoke("nexus:gems"),
    memorySearch: (query) => electron_1.ipcRenderer.invoke("nexus:memory:search", query),
    knowledgeGraph: () => electron_1.ipcRenderer.invoke("nexus:knowledge:graph"),
    tailscaleNodes: () => electron_1.ipcRenderer.invoke("nexus:tailscale:nodes"),
    openAvatarWindow: () => electron_1.ipcRenderer.invoke("nexus:open-avatar"),
    systemStats: () => electron_1.ipcRenderer.invoke("nexus:system-stats"),
    voiceListen: (timeout) => electron_1.ipcRenderer.invoke("nexus:voice:listen", { timeout }),
    voiceSpeak: (text) => electron_1.ipcRenderer.invoke("nexus:voice:speak", { text }),
    voiceStatus: () => electron_1.ipcRenderer.invoke("nexus:voice:status"),
    voicePersonalities: () => electron_1.ipcRenderer.invoke("nexus:voice:personalities"),
    voiceSetPersonality: (personality) => electron_1.ipcRenderer.invoke("nexus:voice:set-personality", { personality }),
    voiceRoute: (query) => electron_1.ipcRenderer.invoke("nexus:voice:route", { query }),
    getConfig: () => electron_1.ipcRenderer.invoke("nexus:get-config"),
    setConfig: (config) => electron_1.ipcRenderer.invoke("nexus:set-config", config),
    zoomGet: () => electron_1.ipcRenderer.invoke("nexus:zoom:get"),
    zoomIn: () => electron_1.ipcRenderer.invoke("nexus:zoom:in"),
    zoomOut: () => electron_1.ipcRenderer.invoke("nexus:zoom:out"),
    zoomReset: () => electron_1.ipcRenderer.invoke("nexus:zoom:reset"),
});
