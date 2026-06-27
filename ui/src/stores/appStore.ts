import { create } from "zustand";
import type { Gema, ChatMessage } from "@/api/nexus";
import { MOCK_GEMAS, sendChatMessage, ensureAuth } from "@/api/nexus";
import { useWSChat, WSStatus } from "@/api/wsChat";
import { API } from "@/api/config";

export type AppView = "home" | "chat" | "gemas" | "manager" | "editor" | "skills" | "settings"
  | "dag" | "sessions" | "brain" | "approvals" | "hive" | "budget" | "doctor" | "hall" | "recipes"
  | "vault" | "commands" | "notes" | "guardian" | "scheduler" | "system" | "creative" | "voice"
  | "cookbook" | "monitor";

// ─── Manager types ─────────────────────────────────────────────────────────

export interface AgentLogEntry {
  time: string;
  text: string;
  type: "info" | "success" | "error" | "log";
}

export interface AgentSlot {
  id: string;
  gemaId: string;
  gemaName: string;
  gemaColor: string;
  status: "idle" | "running" | "done" | "error";
  task: string | null;
  logs: AgentLogEntry[];
  output: string;
  progress: number | null;
  startedAt: number | null;
}

export interface AIModel {
  id: string;
  name: string;
  provider: string;
}

export interface AIProvider {
  id: string;
  name: string;
  baseUrl: string;
  apiKey?: string;
  enabled: boolean;
  free: boolean;
  models: string[];
}

const STORAGE_KEY = "nexus-ai-providers";

function loadProviders(): AIProvider[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return [
    { id: "ollama-default", name: "Ollama (Local)", baseUrl: "http://localhost:11434", enabled: true, free: true, models: ["gemma4:latest", "qwen2.5-coder:7b", "nemotron-3-nano:4b", "deepseek-r1:8b"] },
  ];
}

function saveProviders(providers: AIProvider[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(providers));
}

function buildModelList(providers: AIProvider[]): AIModel[] {
  const models: AIModel[] = [];
  for (const p of providers) {
    if (!p.enabled) continue;
    for (const m of p.models) {
      models.push({ id: `${p.id}::${m}`, name: m, provider: p.name });
    }
  }
  if (models.length === 0) {
    models.push({ id: "auto", name: "Auto (Director)", provider: "ollama" });
  }
  return models;
}

interface AppState {
  view: AppView;
  sidebarCollapsed: boolean;
  sidebarWidth: number;

  gemas: Gema[];
  chatMessages: ChatMessage[];
  chatInput: string;
  activeGema: string | null;
  pendingImages: string[];

  availableModels: AIModel[];
  selectedModel: string;
  aiProviders: AIProvider[];

  // WebSocket streaming state
  wsStatus: WSStatus;
  isStreaming: boolean;
  streamingContent: string;
  streamingGema: string | null;

  // Editor state
  openFiles: string[];
  activeFile: string | null;
  fileContents: Record<string, string>;
  setActiveFile: (path: string | null) => void;
  openFile: (path: string, content: string) => void;
  closeFile: (path: string) => void;
  updateFileContent: (path: string, content: string) => void;

  // Voice state
  isListening: boolean;
  voiceEnabled: boolean;
  avatarOpen: boolean;

  setView: (view: AppView) => void;
  toggleSidebar: () => void;
  setSidebarWidth: (w: number) => void;
  setChatInput: (v: string) => void;
  sendChat: (images?: string[]) => Promise<void>;
  sendChatWS: (message: string, gem?: string, images?: string[]) => void;
  stopStreaming: () => void;
  setActiveGema: (id: string | null) => void;
  setSelectedModel: (id: string) => void;
  addProvider: (p: AIProvider) => void;
  removeProvider: (id: string) => void;
  refreshModels: () => void;
  setIsListening: (v: boolean) => void;
  setVoiceEnabled: (v: boolean) => void;
  setAvatarOpen: (v: boolean) => void;
  setPendingImages: (images: string[]) => void;
  addPendingImage: (image: string) => void;
  clearPendingImages: () => void;

  // Manager
  agentSlots: AgentSlot[];
  addAgentSlot: (gemaId: string, gemaName: string, gemaColor: string) => void;
  removeAgentSlot: (slotId: string) => void;
  startAgentTask: (slotId: string, task: string) => void;
  stopAgentTask: (slotId: string) => void;
  retryAgentTask: (slotId: string) => void;
}

export const useAppStore = create<AppState>((set, get) => {
  const initialProviders = loadProviders();
  const initialModels = buildModelList(initialProviders);

  // WebSocket chat hook
  const wsChat = useWSChat({
    onToken: (token) => {
      set((s) => ({
        streamingContent: s.streamingContent + token,
      }));
    },
    onComplete: (gemUsed, _tokensUsed) => {
      const { streamingContent, chatMessages } = get();
      const botMsg: ChatMessage = {
        id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
        role: "assistant",
        content: streamingContent,
        gema: gemUsed,
        timestamp: new Date().toISOString(),
      };
      set({
        chatMessages: [...chatMessages, botMsg],
        streamingContent: "",
        streamingGema: null,
        isStreaming: false,
      });
      // Auto-TTS if voice enabled — play in browser
      if (get().voiceEnabled && streamingContent) {
        (async () => {
          try {
            const token = localStorage.getItem("nexus-token");
            const headers: Record<string, string> = { "Content-Type": "application/json", "Accept": "audio/wav" };
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${API}/api/voice/speak`, {
              method: "POST", headers,
              body: JSON.stringify({ text: streamingContent, return_audio: true }),
            });
            if (res.ok) {
              const blob = await res.blob();
              const url = URL.createObjectURL(blob);
              const audio = new Audio(url);
              audio.play();
              audio.onended = () => URL.revokeObjectURL(url);
            }
          } catch {}
        })();
      }
    },
    onError: (error) => {
      const { chatMessages } = get();
      const errorMsg: ChatMessage = {
        id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
        role: "assistant",
        content: `Error: ${error}`,
        gema: "system",
        timestamp: new Date().toISOString(),
      };
      set({
        chatMessages: [...chatMessages, errorMsg],
        streamingContent: "",
        streamingGema: null,
        isStreaming: false,
        wsStatus: "error",
      });
    },
  });

  return {
    view: "chat",
    sidebarCollapsed: false,
    sidebarWidth: 240,

    gemas: MOCK_GEMAS,
    chatMessages: [],
    chatInput: "",
    activeGema: null,
    pendingImages: [],

    aiProviders: initialProviders,
    availableModels: initialModels,
    selectedModel: initialModels.find(m => m.id.includes("qwen2.5-coder"))?.id || initialModels[0]?.id || "auto",

    wsStatus: "disconnected",
    isStreaming: false,
    streamingContent: "",
    streamingGema: null,

    openFiles: [],
    activeFile: null,
    fileContents: {},

    isListening: false,
    voiceEnabled: false,
    avatarOpen: false,

    setView: (view) => set({ view }),
    toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    setSidebarWidth: (w) => set({ sidebarWidth: w }),
    setChatInput: (v) => set({ chatInput: v }),
    setActiveGema: (id) => set({ activeGema: id }),
    setSelectedModel: (id) => set({ selectedModel: id }),

    addProvider: (p) => {
      const providers = [...get().aiProviders, p];
      saveProviders(providers);
      const models = buildModelList(providers);
      set({ aiProviders: providers, availableModels: models });
    },

    removeProvider: (id) => {
      const providers = get().aiProviders.filter((p) => p.id !== id);
      saveProviders(providers);
      const models = buildModelList(providers);
      set({ aiProviders: providers, availableModels: models, selectedModel: models[0]?.id || "auto" });
    },

    refreshModels: () => {
      const models = buildModelList(get().aiProviders);
      set({ availableModels: models });
    },

    sendChatWS: (message: string, gem?: string, images?: string[]) => {
      const { chatMessages, activeGema, pendingImages, isStreaming } = get();
      // Dedup guard: prevent double-send
      if (isStreaming) return;
      const lastMsg = chatMessages[chatMessages.length - 1];
      if (lastMsg && lastMsg.role === "user" && lastMsg.content === message && (Date.now() - new Date(lastMsg.timestamp).getTime()) < 2000) return;
      const resolvedGem = gem || (activeGema ? activeGema.replace(/^\d+-/, "") : "auto");
      const hasImages = images && images.length > 0;
      const imageList = images || pendingImages;

      const userMsg: ChatMessage = {
        id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
        role: "user",
        content: hasImages ? (message || "Describe esta imagen") : message,
        timestamp: new Date().toISOString(),
        images: hasImages ? imageList : undefined,
      };

      set({
        chatMessages: [...chatMessages, userMsg],
        chatInput: "",
        pendingImages: hasImages ? [] : pendingImages,
        streamingContent: "",
        streamingGema: resolvedGem,
        isStreaming: true,
        wsStatus: "connected",
      });

      wsChat.sendMessage(message || "Describe esta imagen", resolvedGem, hasImages ? imageList : undefined);
    },

    stopStreaming: () => {
      const { streamingContent, chatMessages, streamingGema } = get();
      if (streamingContent) {
        const botMsg: ChatMessage = {
          id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
          role: "assistant",
          content: streamingContent + "\n\n[Detenido por el usuario]",
          gema: streamingGema || "auto",
          timestamp: new Date().toISOString(),
        };
        set({
          chatMessages: [...chatMessages, botMsg],
        });
      }
      set({
        streamingContent: "",
        streamingGema: null,
        isStreaming: false,
      });
    },

    sendChat: async (images?: string[]) => {
      const { chatInput, chatMessages, activeGema, pendingImages } = get();
      if (!chatInput.trim() && (!images || images.length === 0)) return;

      const imageList = images || pendingImages;
      const hasImages = imageList.length > 0;

      const userMsg: ChatMessage = {
        id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
        role: "user",
        content: chatInput || (hasImages ? "📎 Imagen adjunta" : ""),
        timestamp: new Date().toISOString(),
        images: hasImages ? imageList : undefined,
      };

      set({
        chatMessages: [...chatMessages, userMsg],
        chatInput: "",
        pendingImages: [],
      });

      try {
        await ensureAuth();
        const gem = activeGema ? activeGema.replace(/^\d+-/, "") : "auto";
        const result = await sendChatMessage(chatInput || (hasImages ? "Describe esta imagen" : ""), gem, imageList);

        const botMsg: ChatMessage = {
          id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
          role: "assistant",
          content: result.reply || JSON.stringify(result),
          gema: result.gem_used || gem,
          timestamp: new Date().toISOString(),
        };

        set((s) => ({
          chatMessages: [...s.chatMessages, botMsg],
        }));
      } catch (err) {
        const errorMsg: ChatMessage = {
          id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
          role: "assistant",
          content: `Error conectando con el backend: ${err instanceof Error ? err.message : String(err)}`,
          gema: "system",
          timestamp: new Date().toISOString(),
        };
        set((s) => ({
          chatMessages: [...s.chatMessages, errorMsg],
        }));
      }
    },

    setIsListening: (v) => set({ isListening: v }),
    setVoiceEnabled: (v) => set({ voiceEnabled: v }),
    setAvatarOpen: (v) => set({ avatarOpen: v }),

    setActiveFile: (path) => set({ activeFile: path }),
    openFile: (path, content) =>
      set((s) => ({
        openFiles: s.openFiles.includes(path) ? s.openFiles : [...s.openFiles, path],
        activeFile: path,
        fileContents: { ...s.fileContents, [path]: content },
      })),
    closeFile: (path) =>
      set((s) => {
        const idx = s.openFiles.indexOf(path);
        const nextFiles = s.openFiles.filter((p) => p !== path);
        const nextContents = { ...s.fileContents };
        delete nextContents[path];
        return {
          openFiles: nextFiles,
          activeFile: s.activeFile === path
            ? (nextFiles[Math.min(idx, nextFiles.length - 1)] ?? null)
            : s.activeFile,
          fileContents: nextContents,
        };
      }),
    updateFileContent: (path, content) =>
      set((s) => ({
        fileContents: { ...s.fileContents, [path]: content },
      })),

    setPendingImages: (images) => set({ pendingImages: images }),
    addPendingImage: (image) => set((s) => ({ pendingImages: [...s.pendingImages, image] })),
    clearPendingImages: () => set({ pendingImages: [] }),

    // ─── Manager ───────────────────────────────────────────────────────
    agentSlots: [],

    addAgentSlot: (gemaId, gemaName, gemaColor) => {
      const slot: AgentSlot = {
        id: (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36)),
        gemaId,
        gemaName,
        gemaColor,
        status: "idle",
        task: null,
        logs: [],
        output: "",
        progress: null,
        startedAt: null,
      };
      set((s) => ({ agentSlots: [...s.agentSlots, slot] }));
    },

    removeAgentSlot: (slotId) => {
      set((s) => ({ agentSlots: s.agentSlots.filter((x) => x.id !== slotId) }));
    },

    startAgentTask: (slotId, task) => {
      const now = Date.now();
      const timeStr = () => new Date().toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

      set((s) => ({
        agentSlots: s.agentSlots.map((slot) =>
          slot.id === slotId
            ? {
                ...slot,
                status: "running" as const,
                task,
                output: "",
                progress: null,
                startedAt: now,
                logs: [
                  ...slot.logs,
                  { time: timeStr(), text: `Tarea asignada: ${task}`, type: "info" as const },
                ],
              }
            : slot
        ),
      }));

      // Fire WS request to backend
      const slot = get().agentSlots.find((x) => x.id === slotId);
      if (!slot) return;
      const gem = slot.gemaId.replace(/^\d+-/, "");

      fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: task, gem, project: "default" }),
      })
        .then(async (res) => {
          const data = await res.json();
          const reply = data.reply || data.content || JSON.stringify(data);
          set((s) => ({
            agentSlots: s.agentSlots.map((x) =>
              x.id === slotId
                ? {
                    ...x,
                    status: "done" as const,
                    output: reply,
                    progress: 100,
                    logs: [
                      ...x.logs,
                      { time: timeStr(), text: "Tarea completada", type: "success" as const },
                    ],
                  }
                : x
            ),
          }));
        })
        .catch((err) => {
          set((s) => ({
            agentSlots: s.agentSlots.map((x) =>
              x.id === slotId
                ? {
                    ...x,
                    status: "error" as const,
                    output: `Error: ${err instanceof Error ? err.message : String(err)}`,
                    logs: [
                      ...x.logs,
                      { time: timeStr(), text: `Error: ${err instanceof Error ? err.message : String(err)}`, type: "error" as const },
                    ],
                  }
                : x
            ),
          }));
        });
    },

    stopAgentTask: (slotId) => {
      const timeStr = new Date().toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
      set((s) => ({
        agentSlots: s.agentSlots.map((x) =>
          x.id === slotId
            ? {
                ...x,
                status: "done" as const,
                output: x.output + "\n\n[Detenido por el usuario]",
                logs: [...x.logs, { time: timeStr, text: "Detenido por el usuario", type: "info" as const }],
              }
            : x
        ),
      }));
    },

    retryAgentTask: (slotId) => {
      const slot = get().agentSlots.find((x) => x.id === slotId);
      if (slot?.task) {
        get().startAgentTask(slotId, slot.task);
      }
    },
  };
});
