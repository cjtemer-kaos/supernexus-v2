const API_BASE = typeof window !== "undefined" && window.location.port === "3000"
  ? "/api"
  : "http://localhost:9001/api";
const TOKEN_KEY = "nexus-token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export async function nexusLogin(username: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  const token = data.token || data.access_token;
  if (!token) throw new Error("No token in response");
  setToken(token);
  return token;
}

export async function ensureAuth(): Promise<string> {
  const existing = getToken();
  if (existing) return existing;
  return nexusLogin("nexus", "nexus2026");
}

export async function nexusFetch<T = unknown>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = await ensureAuth();
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (res.status === 401 || res.status === 403) {
    localStorage.removeItem(TOKEN_KEY);
    const newToken = await nexusLogin("nexus", "nexus2026");
    const retry = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${newToken}`,
        ...options?.headers,
      },
    });
    if (!retry.ok) throw new Error(`Nexus API ${retry.status}: ${retry.statusText}`);
    return retry.json();
  }
  if (!res.ok) throw new Error(`Nexus API ${res.status}: ${res.statusText}`);
  return res.json();
}

interface ChatResponse {
  reply: string;
  gem_used: string;
  model: string;
  tokens_used: number;
  duration_ms: number;
  success: boolean;
}

export async function sendChatMessage(message: string, gem = "auto"): Promise<ChatResponse> {
  return nexusFetch("/chat", {
    method: "POST",
    body: JSON.stringify({ message, gem, project: "default", voice: false, images: [], files: [] }),
  });
}

export interface Gema {
  id: string;
  name: string;
  description: string;
  model: string;
  tools: string[];
  status: "active" | "idle" | "error" | "loading";
  color: string;
}


export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  gema?: string;
  timestamp: string;
}

export interface NexusStatus {
  online: boolean;
  gems_active: number;
  nodes_online: number;
  tokens_used: number;
  uptime: string;
}

// Mock data for development without backend
export const MOCK_GEMAS: Gema[] = [
  { id: "01-director", name: "Director", description: "Planificador principal y orquestador de la colmena. Descompone tareas en grafos.", model: "deepseek-r1:8b", tools: ["task_queue", "dag_coordinator"], status: "active", color: "#06b6d4" },
  { id: "02-code", name: "Code", description: "Escritor de codigo y refactorizador experto.", model: "qwen2.5-coder:7b", tools: ["replace_file", "lsp_client"], status: "active", color: "#3b82f6" },
  { id: "03-scholar", name: "Scholar", description: "Investigador web y sintetizador de informacion tecnica.", model: "deepseek-r1:8b", tools: ["web_search", "web_fetch"], status: "idle", color: "#8b5cf6" },
  { id: "04-architect", name: "Architect", description: "Disenador de sistemas, grafos de dependencias y UMLs.", model: "qwen2.5-coder:7b", tools: ["code_analyzer", "mermaid_render"], status: "idle", color: "#6366f1" },
  { id: "05-creative", name: "Creative", description: "Generador de prompts artisticos y documentacion creativa.", model: "qwen2.5-coder:7b", tools: ["markdown_gen", "image_gen"], status: "idle", color: "#f97316" },
  { id: "06-sage", name: "Sage", description: "Guardian de la memoria asociativa a largo plazo.", model: "deepseek-r1:8b", tools: ["knowledge_vault", "fts5_search"], status: "active", color: "#10b981" },
  { id: "07-analyst", name: "Analyst", description: "Procesador cuantitativo de datos y KPIs.", model: "qwen2.5-coder:7b", tools: ["python_exec", "pandas_stats"], status: "idle", color: "#0ea5e9" },
  { id: "08-engineer", name: "Engineer", description: "Scripting de sistemas y automatizacion CLI.", model: "qwen2.5-coder:7b", tools: ["persistent_shell", "git_status"], status: "idle", color: "#78716c" },
  { id: "09-debugger", name: "Debugger", description: "Analista de trazas de error y excepciones.", model: "deepseek-r1:8b", tools: ["lsp_diagnostics", "logs_viewer"], status: "idle", color: "#f43f5e" },
  { id: "10-optimizer", name: "Optimizer", description: "Perfilador de rendimiento y compresion de prompts.", model: "qwen2.5-coder:7b", tools: ["optimize_prompt", "lru_cache"], status: "idle", color: "#eab308" },
  { id: "11-tester", name: "Tester", description: "Creador de suites QA, mocks y tests unitarios.", model: "qwen2.5-coder:7b", tools: ["pytest_runner", "simulation"], status: "idle", color: "#a3e635" },
  { id: "12-security", name: "Security", description: "Auditor estatico contra RCE, SQLi, SSRF y secretos.", model: "deepseek-r1:8b", tools: ["risk_assessor", "osv_scanner"], status: "idle", color: "#ef4444" },
  { id: "13-devops", name: "DevOps", description: "Orquestador de Docker y despliegues.", model: "qwen2.5-coder:7b", tools: ["docker_client", "tailscale"], status: "idle", color: "#14b8a6" },
  { id: "14-trainer", name: "Trainer", description: "Generador de manuales y tutoriales interactivos.", model: "qwen2.5-coder:7b", tools: ["explain_concept", "curriculum"], status: "idle", color: "#f472b6" },
  { id: "15-biblioteca", name: "Biblioteca", description: "Indexador de 4,051 habilidades agenciales.", model: "deepseek-r1:8b", tools: ["skill_curator", "skill_registry"], status: "active", color: "#a78bfa" },
  { id: "16-vision", name: "Vision", description: "Captura de pantalla, analisis de imagenes y OCR.", model: "moondream2", tools: ["screenshot", "ocr_read", "yolo_detect"], status: "idle", color: "#2dd4bf" },
  { id: "17-opencode", name: "OpenCode", description: "Agente ejecutor interactivo CLI.", model: "qwen2.5-coder:7b", tools: ["opencode_shell", "task_delegator"], status: "active", color: "#fb923c" },
  { id: "18-codex", name: "Codex", description: "Ejecutor de codigo en sandboxes locales.", model: "qwen2.5-coder:7b", tools: ["python_sandbox", "node_sandbox"], status: "idle", color: "#38bdf8" },
  { id: "19-design", name: "Design", description: "Maquetador de interfaces web CSS y componentes.", model: "qwen2.5-coder:7b", tools: ["html_gen", "css_theme"], status: "idle", color: "#c084fc" },
  { id: "20-music", name: "Music", description: "Pipelines de voz, sintesis TTS y conversion de audio.", model: "qwen2.5-coder:7b", tools: ["tts_generate", "stt_transcribe"], status: "idle", color: "#fb7185" },
  { id: "21-prompter", name: "Prompter", description: "Ingenieria de prompts y alineacion de temperaturas.", model: "qwen2.5-coder:7b", tools: ["prompt_compressor", "aggregator"], status: "idle", color: "#fbbf24" },
  { id: "22-producer", name: "Producer", description: "Automatizacion via RCON y agendamiento de tareas.", model: "qwen2.5-coder:7b", tools: ["rcon_client", "cron_scheduler"], status: "idle", color: "#4ade80" },
];

