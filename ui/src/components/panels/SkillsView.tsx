import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Sparkles, RefreshCw, Search, Tag } from "lucide-react";



interface Skill { name: string; description: string; category?: string; tags?: string[]; }

export function SkillsView() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/ai/tools`);
      const data = await res.json();
      const list: Skill[] = data.tools || data.skills || data || [];
      setSkills(list);
      const cats = [...new Set(list.map((s) => s.category).filter(Boolean))] as string[];
      setCategories(cats.sort());
    } catch { setSkills([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const filtered = skills.filter((s) => {
    if (activeCategory && s.category !== activeCategory) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return s.name?.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q) || s.tags?.some((t) => t.toLowerCase().includes(q));
  });

  return (
    <div className="p-6 max-w-[1400px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Sparkles size={22} className="text-[var(--color-nexus-accent)]" /> Skills
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">{skills.length.toLocaleString()} habilidades indexadas</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-3 text-[var(--color-nexus-muted)]" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar skills por nombre, descripción o tag..."
          className="w-full bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl pl-9 pr-4 py-2.5 text-sm text-[var(--color-nexus-text)] outline-none focus:border-[var(--color-nexus-accent)]" />
      </div>

      {/* Categories */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <button onClick={() => setActiveCategory(null)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors ${!activeCategory ? "bg-[var(--color-nexus-accent)] text-white" : "bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]"}`}>
            Todas
          </button>
          {categories.map((c) => (
            <button key={c} onClick={() => setActiveCategory(c === activeCategory ? null : c)}
              className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors ${activeCategory === c ? "bg-[var(--color-nexus-accent)] text-white" : "bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]"}`}>
              {c}
            </button>
          ))}
        </div>
      )}

      {/* Skills grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {filtered.slice(0, 100).map((s) => (
          <div key={s.name} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-3">
            <div className="text-xs font-semibold text-[var(--color-nexus-text)] mb-1 truncate">{s.name}</div>
            <p className="text-[10px] text-[var(--color-nexus-text-sub)] line-clamp-2 mb-2">{s.description}</p>
            {s.tags && (
              <div className="flex flex-wrap gap-1">
                {s.tags.slice(0, 3).map((t) => (
                  <span key={t} className="flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
                    <Tag size={8} />{t}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {filtered.length > 100 && (
        <div className="text-center text-xs text-[var(--color-nexus-muted)]">Mostrando 100 de {filtered.length} resultados</div>
      )}
      {filtered.length === 0 && !loading && (
        <div className="text-center py-12 text-sm text-[var(--color-nexus-muted)]">Sin resultados</div>
      )}
    </div>
  );
}
