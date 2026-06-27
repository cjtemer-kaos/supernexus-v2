interface NexusAPI {
  chat: (message: string, gem?: string, project?: string, model?: string, attachments?: string[], voice?: boolean) => Promise<{ content: string; gem?: string; audio?: string }>;
  status: () => Promise<{ online: boolean }>;
  projects: () => Promise<{ projects: string[] }>;
  gems: () => Promise<{ gems: Array<{ name: string; tags: string[]; description: string; model: string; execution_count: number; success_rate: number }> }>;
  memorySearch: (query: string) => Promise<{ results: any[] }>;
  knowledgeGraph: () => Promise<{ nodes: any[]; edges: any[] }>;
  tailscaleNodes: () => Promise<{ nodes: any[] }>;
  openAvatarWindow: () => void;
  systemStats: () => Promise<{ cpu: number; memory: number; gpu: number; disk: number; cpu_usage?: number; ram_usage?: number; gpu_usage?: number; disk_usage?: number }>;
  voiceListen: (timeout?: number) => Promise<{ text: string }>;
  voiceSpeak: (text: string) => Promise<void>;
  voiceStatus: () => Promise<{ ready: boolean; listening: boolean; personalities?: any[]; personality?: string }>;
  voicePersonalities: () => Promise<{ personalities: Array<{ id: string; name: string; voice: string; description: string }> }>;
  voiceSetPersonality: (personality: string) => Promise<{ success: boolean }>;
  voiceRoute: (query: string) => Promise<{ personality: string }>;
  getModels: () => Promise<{ models: Array<{ id: string; name: string; provider: string }> }>;
  setModel: (modelId: string) => Promise<{ success: boolean }>;
  getConfig: () => Promise<any>;
  setConfig: (config: any) => Promise<{ success: boolean }>;
}

declare global {
  interface Window {
    nexusAPI: NexusAPI;
  }
}

export {};
