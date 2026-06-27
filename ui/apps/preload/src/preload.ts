import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("nexusAPI", {
  chat: (message: string, gem?: string, project?: string, model?: string, attachments?: string[], voice?: boolean) => 
    ipcRenderer.invoke("nexus:chat", { message, gem, project, model, attachments, voice }),
  status: () => ipcRenderer.invoke("nexus:status"),
  projects: () => ipcRenderer.invoke("nexus:projects"),
  gems: () => ipcRenderer.invoke("nexus:gems"),
  memorySearch: (query: string) => ipcRenderer.invoke("nexus:memory:search", query),
  knowledgeGraph: () => ipcRenderer.invoke("nexus:knowledge:graph"),
  tailscaleNodes: () => ipcRenderer.invoke("nexus:tailscale:nodes"),
  openAvatarWindow: () => ipcRenderer.invoke("nexus:open-avatar"),
  systemStats: () => ipcRenderer.invoke("nexus:system-stats"),
  voiceListen: (timeout?: number) => ipcRenderer.invoke("nexus:voice:listen", { timeout }),
  voiceSpeak: (text: string) => ipcRenderer.invoke("nexus:voice:speak", { text }),
  voiceStatus: () => ipcRenderer.invoke("nexus:voice:status"),
  voicePersonalities: () => ipcRenderer.invoke("nexus:voice:personalities"),
  voiceSetPersonality: (personality: string) => ipcRenderer.invoke("nexus:voice:set-personality", { personality }),
  voiceRoute: (query: string) => ipcRenderer.invoke("nexus:voice:route", { query }),
  getConfig: () => ipcRenderer.invoke("nexus:get-config"),
  setConfig: (config: any) => ipcRenderer.invoke("nexus:set-config", config),
});
