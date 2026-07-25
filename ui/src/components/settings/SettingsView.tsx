import { useAppStore } from "@/stores/appStore";
import {
  ArrowLeft, Settings2, Eye, EyeOff, Check, X,
  Target, Code2, BookOpen, Building2, Palette, Brain, BarChart3,
  Wrench, Search, Zap, FlaskConical, Shield, Rocket, GraduationCap,
  Library, Terminal, Box, Figma, Music, PenTool, Clapperboard,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

// ─── Provider presets (Goose-style grid) ────────────────────────────────────

const ALL_PROVIDERS: { id: string; name: string; desc: string; url: string; free: boolean; keyPlaceholder?: string }[] = [
  { id: "ollama", name: "Ollama (Local)", desc: "Modelos locales via Ollama. Sin API key, 100% privado.", url: "http://localhost:11434", free: true },
  { id: "openai", name: "OpenAI", desc: "GPT-4o, GPT-4o-mini, o1 y modelos de OpenAI.", url: "https://api.openai.com/v1", free: false, keyPlaceholder: "sk-..." },
  { id: "anthropic", name: "Anthropic", desc: "Claude Opus, Sonnet, Haiku de Anthropic.", url: "https://api.anthropic.com", free: false, keyPlaceholder: "sk-ant-..." },
  { id: "google", name: "Google Gemini", desc: "Gemini Flash gratis, Pro y Ultra de pago.", url: "https://generativelanguage.googleapis.com/v1beta", free: true, keyPlaceholder: "AIza..." },
  { id: "groq", name: "Groq", desc: "Inferencia ultra-rapida. Tier gratis con Llama y Mixtral.", url: "https://api.groq.com/openai/v1", free: true, keyPlaceholder: "gsk_..." },
  { id: "deepseek", name: "DeepSeek", desc: "DeepSeek V3, R1. Muy economico.", url: "https://api.deepseek.com/v1", free: false, keyPlaceholder: "sk-..." },
  { id: "together", name: "Together AI", desc: "Llama, Mistral, Qwen y 100+ modelos open-source.", url: "https://api.together.xyz/v1", free: false, keyPlaceholder: "..." },
  { id: "openrouter", name: "OpenRouter", desc: "Gateway a 200+ modelos con una sola API key.", url: "https://openrouter.ai/api/v1", free: false, keyPlaceholder: "sk-or-..." },
  { id: "cerebras", name: "Cerebras", desc: "Inferencia rapida en hardware wafer-scale.", url: "https://api.cerebras.ai/v1", free: false, keyPlaceholder: "csk-..." },
  { id: "azure", name: "Azure OpenAI", desc: "Modelos de OpenAI via Azure con credenciales corporativas.", url: "https://YOUR_RESOURCE.openai.azure.com", free: false, keyPlaceholder: "..." },
  { id: "bedrock", name: "Amazon Bedrock", desc: "Claude, Llama, Titan via AWS Bedrock.", url: "https://bedrock-runtime.us-east-1.amazonaws.com", free: false, keyPlaceholder: "AKIA..." },
  { id: "vertex", name: "GCP Vertex AI", desc: "Gemini, Claude y otros modelos via Google Cloud.", url: "https://us-central1-aiplatform.googleapis.com", free: false, keyPlaceholder: "..." },
  { id: "mistral", name: "Mistral AI", desc: "Mistral Large, Medium, Small y Codestral.", url: "https://api.mistral.ai/v1", free: false, keyPlaceholder: "..." },
  { id: "avian", name: "Avian", desc: "Inferencia economica con DeepSeek, Kimi, GLM y MiniMax.", url: "https://api.avian.io/v1", free: false, keyPlaceholder: "..." },
  { id: "custom", name: "Custom (OpenAI-compatible)", desc: "Cualquier API compatible con el formato OpenAI.", url: "", free: false, keyPlaceholder: "..." },
];

// ─── Gema extension definitions ─────────────────────────────────────────────

const GEMA_ICON_MAP: Record<string, LucideIcon> = {
  Director: Target, Code: Code2, Scholar: BookOpen, Architect: Building2,
  Creative: Palette, Sage: Brain, Analyst: BarChart3, Engineer: Wrench,
  Debugger: Search, Optimizer: Zap, Tester: FlaskConical, Security: Shield,
  DevOps: Rocket, Trainer: GraduationCap, Biblioteca: Library, Vision: Eye,
  OpenCode: Terminal, Codex: Box, Design: Figma, Music: Music,
  Prompter: PenTool, Producer: Clapperboard,
};

// ─── Configure modal ────────────────────────────────────────────────────────

function ConfigureModal({
  preset,
  onClose,
  onSave,
}: {
  preset: typeof ALL_PROVIDERS[0];
  onClose: () => void;
  onSave: (apiKey: string, baseUrl: string) => void;
}) {
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(preset.url);
  const [showKey, setShowKey] = useState(false);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-6 w-full max-w-lg space-y-4 animate-nexus-in"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-[var(--color-nexus-text)]">Configurar {preset.name}</h3>
          <button onClick={onClose} className="p-1 rounded-md hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
            <X size={16} />
          </button>
        </div>

        <p className="text-xs text-[var(--color-nexus-text-sub)]">{preset.desc}</p>

        <div className="space-y-1.5">
          <label className="text-xs text-[var(--color-nexus-text-sub)]">URL Base</label>
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] font-mono outline-none focus:border-[var(--color-nexus-accent)]"
          />
        </div>

        {!preset.free && (
          <div className="space-y-1.5">
            <label className="text-xs text-[var(--color-nexus-text-sub)]">API Key</label>
            <div className="flex items-center gap-2">
              <input
                type={showKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={preset.keyPlaceholder || "sk-..."}
                className="flex-1 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] font-mono outline-none focus:border-[var(--color-nexus-accent)] placeholder:text-[var(--color-nexus-muted)]"
              />
              <button onClick={() => setShowKey(!showKey)} className="p-2 text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]">
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
        )}

        <div className="flex gap-2 pt-2">
          <button
            onClick={() => {
              if (!preset.free && !apiKey.trim()) {
                toast.error("Se requiere API key");
                return;
              }
              onSave(apiKey, baseUrl);
            }}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] transition-colors"
          >
            <Check size={14} />
            Guardar
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-text-sub)] hover:text-[var(--color-nexus-text)] transition-colors"
          >
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Toggle switch ──────────────────────────────────────────────────────────

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={`relative w-9 h-5 rounded-full transition-colors ${checked ? "bg-[var(--color-nexus-accent)]" : "bg-[var(--color-nexus-surface-2)]"}`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${checked ? "translate-x-4" : ""}`}
      />
    </button>
  );
}

// ─── Main Settings View ─────────────────────────────────────────────────────

export function SettingsView() {
  const { aiProviders, addProvider, removeProvider, gemas } = useAppStore();
  const [configuring, setConfiguring] = useState<typeof ALL_PROVIDERS[0] | null>(null);
  const [view, setView] = useState<"main" | "providers">("main");
  const [gemaStates, setGemaStates] = useState<Record<string, boolean>>(() => {
    const s: Record<string, boolean> = {};
    gemas.forEach((g) => { s[g.id] = g.status === "active"; });
    return s;
  });

  const configuredIds = new Set(aiProviders.map((p) => p.id.replace(/-\d+$/, "")));

  const handleSaveProvider = (apiKey: string, baseUrl: string) => {
    if (!configuring) return;
    addProvider({
      id: `${configuring.id}-${Date.now()}`,
      name: configuring.name,
      baseUrl,
      apiKey: apiKey || undefined,
      enabled: true,
      free: configuring.free,
      models: [],
    });
    toast.success(`${configuring.name} configurado`);
    setConfiguring(null);
  };

  const toggleGema = (id: string) => {
    setGemaStates((s) => ({ ...s, [id]: !s[id] }));
  };

  // ── Providers sub-view (Goose-style grid) ──

  if (view === "providers") {
    return (
      <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
        <button
          onClick={() => setView("main")}
          className="flex items-center gap-2 text-sm text-[var(--color-nexus-accent)] hover:underline"
        >
          <ArrowLeft size={16} />
          Volver
        </button>

        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)]">Proveedores de IA</h1>
          <div className="h-px bg-[var(--color-nexus-border)] mt-4" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {ALL_PROVIDERS.map((preset) => {
            const isConfigured = configuredIds.has(preset.id);
            return (
              <div
                key={preset.id}
                className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 flex flex-col justify-between min-h-[160px] hover:border-[var(--color-nexus-accent)]/40 transition-colors"
              >
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-semibold text-[var(--color-nexus-text)]">{preset.name}</span>
                    {isConfigured && (
                      <Check size={14} className="text-[var(--color-nexus-online)]" />
                    )}
                  </div>
                  <p className="text-xs text-[var(--color-nexus-text-sub)] leading-relaxed line-clamp-3">
                    {preset.desc}
                  </p>
                </div>

                <div className="flex items-center gap-2 mt-3">
                  <button
                    onClick={() => setConfiguring(preset)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-text-sub)] hover:text-[var(--color-nexus-text)] hover:bg-[var(--color-nexus-border)] transition-colors"
                  >
                    <Settings2 size={12} />
                    Configurar
                  </button>
                  {isConfigured && (
                    <button
                      onClick={() => {
                        const p = aiProviders.find((x) => x.id.startsWith(preset.id));
                        if (p) { removeProvider(p.id); toast.success(`${preset.name} eliminado`); }
                      }}
                      className="px-2 py-1.5 rounded-lg text-xs text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-error)] transition-colors"
                    >
                      <X size={12} />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {configuring && (
          <ConfigureModal
            preset={configuring}
            onClose={() => setConfiguring(null)}
            onSave={handleSaveProvider}
          />
        )}
      </div>
    );
  }

  // ── Main settings view ──

  const activeGemas = Object.values(gemaStates).filter(Boolean).length;

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-8 animate-nexus-in overflow-y-auto h-full">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-nexus-text)]">Configuracion</h1>
        <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Proveedores de IA y extensiones de gemas</p>
      </div>

      {/* Providers summary */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-medium tracking-wider uppercase text-[var(--color-nexus-muted)]">
            Proveedores de IA ({aiProviders.length} configurados)
          </h2>
          <button
            onClick={() => setView("providers")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] transition-colors"
          >
            <Settings2 size={13} />
            Administrar proveedores
          </button>
        </div>

        {aiProviders.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {aiProviders.map((p) => (
              <div key={p.id} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3 flex items-center gap-3">
                <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-nexus-online)] shrink-0" />
                <div className="min-w-0">
                  <div className="text-sm font-medium text-[var(--color-nexus-text)] truncate">{p.name}</div>
                  <div className="text-[10px] text-[var(--color-nexus-muted)] font-mono truncate">{p.baseUrl}</div>
                </div>
                {p.free && (
                  <span className="ml-auto text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[var(--color-nexus-online)]/15 text-[var(--color-nexus-online)] shrink-0">
                    GRATIS
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 text-sm text-[var(--color-nexus-muted)] bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl">
            No hay proveedores configurados. Agrega uno para empezar.
          </div>
        )}
      </div>

      {/* Gema Extensions */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-medium tracking-wider uppercase text-[var(--color-nexus-muted)]">
              Gemas / Extensiones ({activeGemas} activas)
            </h2>
            <p className="text-xs text-[var(--color-nexus-text-sub)] mt-1">
              Las gemas activas estan disponibles para el Director durante el chat.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {gemas.map((g) => {
            const Icon = GEMA_ICON_MAP[g.name] || Target;
            const enabled = gemaStates[g.id] ?? false;
            return (
              <div
                key={g.id}
                className={`bg-[var(--color-nexus-surface)] border rounded-xl p-4 transition-colors ${
                  enabled ? "border-[var(--color-nexus-border)]" : "border-[var(--color-nexus-border)] opacity-60"
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                      style={{ backgroundColor: `${g.color}15` }}
                    >
                      <Icon size={14} style={{ color: g.color }} />
                    </div>
                    <span className="text-sm font-semibold text-[var(--color-nexus-text)]">{g.name}</span>
                  </div>
                  <Toggle checked={enabled} onChange={() => toggleGema(g.id)} />
                </div>
                <p className="text-xs text-[var(--color-nexus-text-sub)] leading-relaxed line-clamp-2">
                  {g.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Info footer */}
      <div className="bg-[var(--color-nexus-surface-2)] rounded-xl p-4 text-xs text-[var(--color-nexus-muted)] space-y-1">
        <p>Las API keys se guardan localmente en tu navegador y se envian al backend de SuperNEXUS para las llamadas.</p>
        <p>Los proveedores gratuitos (Ollama, Groq, Gemini) no requieren API key o tienen tier gratuito.</p>
      </div>
    </div>
  );
}
