import { create } from "zustand";
import type { Gema, ChatMessage } from "@/api/nexus";
import { MOCK_GEMAS, sendChatMessage, ensureAuth } from "@/api/nexus";
import { useWSChat, WSStatus } from "@/api/wsChat";

export type AppView = "home" | "chat" | "gemas" | "skills" | "vision" | "brain" | "settings";

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
    { id: "ollama-default", name: "Ollama (Local)", baseUrl: "http://localhost:11434", enabled: true, free: true, models: ["qwen2.5:0.5b", "deepseek-r1:8b", "qwen2.5-coder:7b"] },
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

  availableModels: AIModel[];
  selectedModel: string;
  aiProviders: AIProvider[];

  // WebSocket streaming state
  wsStatus: WSStatus;
  isStreaming: boolean;
  streamingContent: string;
  streamingGema: string | null;

  setView: (view: AppView) => void;
  toggleSidebar: () => void;
  setSidebarWidth: (w: number) => void;
  setChatInput: (v: string) => void;
  sendChat: () => Promise<void>;
  sendChatWS: (message: string, gem?: string) => void;
  stopStreaming: () => void;
  setActiveGema: (id: string | null) => void;
  setSelectedModel: (id: string) => void;
  addProvider: (p: AIProvider) => void;
  removeProvider: (id: string) => void;
  refreshModels: () => void;
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
        id: crypto.randomUUID(),
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
    },
    onError: (error) => {
      const { chatMessages } = get();
      const errorMsg: ChatMessage = {
        id: crypto.randomUUID(),
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
    view: "home",
    sidebarCollapsed: false,
    sidebarWidth: 240,

    gemas: MOCK_GEMAS,
    chatMessages: [],
    chatInput: "",
    activeGema: null,

    aiProviders: initialProviders,
    availableModels: initialModels,
    selectedModel: initialModels[0]?.id || "auto",

    wsStatus: "disconnected",
    isStreaming: false,
    streamingContent: "",
    streamingGema: null,

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

    sendChatWS: (message: string, gem?: string) => {
      const { chatMessages, activeGema } = get();
      const resolvedGem = gem || (activeGema ? activeGema.replace(/^\d+-/, "") : "auto");

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: message,
        timestamp: new Date().toISOString(),
      };

      set({
        chatMessages: [...chatMessages, userMsg],
        streamingContent: "",
        streamingGema: resolvedGem,
        isStreaming: true,
        wsStatus: "connected",
      });

      wsChat.sendMessage(message, resolvedGem);
    },

    stopStreaming: () => {
      const { streamingContent, chatMessages, streamingGema } = get();
      if (streamingContent) {
        const botMsg: ChatMessage = {
          id: crypto.randomUUID(),
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

    sendChat: async () => {
      const { chatInput, chatMessages, activeGema } = get();
      if (!chatInput.trim()) return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: chatInput,
        timestamp: new Date().toISOString(),
      };

      set({
        chatMessages: [...chatMessages, userMsg],
        chatInput: "",
      });

      try {
        await ensureAuth();
        const gem = activeGema ? activeGema.replace(/^\d+-/, "") : "auto";
        const result = await sendChatMessage(chatInput, gem);

        const botMsg: ChatMessage = {
          id: crypto.randomUUID(),
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
          id: crypto.randomUUID(),
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
  };
});
