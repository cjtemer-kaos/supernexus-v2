import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Brain, RefreshCw, Search, BookOpen, Lightbulb, Download } from "lucide-react";



interface BrainStats { topics: number; total_entries: number; sources: Record<string, number>; avg_importance: number; }
interface KnowledgeEntry { topic: string; content: string; source: string; importance: number; created_at: string; }

export function BrainView() {
  const [stats, setStats] = useState<BrainStats | null>(null);
  const [knowledge, setKnowledge] = useState<KnowledgeEntry[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [learnTopic, setLearnTopic] = useState("");
  const [learnContent, setLearnContent] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [sRes, kRes] = await Promise.all([
        authFetch(`${API}/api/brain/stats`),
        authFetch(`${API}/api/brain/knowledge`),
      ]);
      setStats(await sRes.json());
      const kData = await kRes.json();
      setKnowledge(kData.entries || kData.knowledge || kData || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const learn = async () => {
    if (!learnTopic.trim() || !learnContent.trim()) return;
    await authFetch(`${API}/api/brain/learn`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic: learnTopic, content: learnContent, source: "ui-manual" }),
    });
    setLearnTopic(""); setLearnContent("");
    refresh();
  };

  const filtered = search ? knowledge.filter((k) => k.topic?.toLowerCase().includes(search.toLowerCase()) || k.content?.toLowerCase().includes(search.toLowerCase())) : knowledge;

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Brain size={22} className="text-[var(--color-nexus-accent)]" /> Cerebro
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Conocimiento aprendido, estadísticas y memoria a largo plazo</p>
        </div>
        <div className="flex gap-2">
          <a href={`${API}/api/brain/export`} target="_blank" rel="noreferrer"
            className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)]">
            <Download size={14} />
          </a>
          <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: "Temas", value: stats.topics, icon: BookOpen },
            { label: "Entradas", value: stats.total_entries, icon: Lightbulb },
            { label: "Fuentes", value: Object.keys(stats.sources || {}).length, icon: Brain },
            { label: "Importancia avg", value: (stats.avg_importance || 0).toFixed(1), icon: Search },
          ].map((s) => (
            <div key={s.label} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
              <div className="flex items-center gap-2 text-[10px] text-[var(--color-nexus-muted)] uppercase tracking-wider mb-1">
                <s.icon size={12} /> {s.label}
              </div>
              <div className="text-xl font-bold text-[var(--color-nexus-text)]">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Teach */}
      <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-2">
        <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">Enseñar al cerebro</div>
        <div className="flex gap-2">
          <input value={learnTopic} onChange={(e) => setLearnTopic(e.target.value)} placeholder="Tema..."
            className="w-40 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none focus:border-[var(--color-nexus-accent)]" />
          <input value={learnContent} onChange={(e) => setLearnContent(e.target.value)} onKeyDown={(e) => e.key === "Enter" && learn()} placeholder="Contenido a aprender..."
            className="flex-1 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none focus:border-[var(--color-nexus-accent)]" />
          <button onClick={learn} disabled={!learnTopic.trim() || !learnContent.trim()}
            className="px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-30 transition-colors">
            Aprender
          </button>
        </div>
      </div>

      {/* Search + knowledge list */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-3 text-[var(--color-nexus-muted)]" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar en el conocimiento..."
          className="w-full bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl pl-9 pr-4 py-2.5 text-sm text-[var(--color-nexus-text)] outline-none focus:border-[var(--color-nexus-accent)]" />
      </div>

      <div className="space-y-2">
        {filtered.slice(0, 50).map((k, i) => (
          <div key={i} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold text-[var(--color-nexus-accent)]">{k.topic}</span>
              <span className="text-[10px] text-[var(--color-nexus-muted)] font-mono">{k.source}</span>
              <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]">★{k.importance}</span>
            </div>
            <div className="text-xs text-[var(--color-nexus-text)] line-clamp-3">{k.content}</div>
          </div>
        ))}
        {filtered.length === 0 && <div className="text-center py-8 text-sm text-[var(--color-nexus-muted)]">Sin resultados</div>}
      </div>
    </div>
  );
}
