import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { BookMarked, Play, RefreshCw, Loader2 } from "lucide-react";



interface Recipe { name: string; description: string; steps: string[]; tags?: string[]; }

export function RecipesView() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/recipes`);
      const data = await res.json();
      setRecipes(data.recipes || data || []);
    } catch { setRecipes([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const execute = async (name: string) => {
    setRunning(name); setResult(null);
    try {
      const res = await authFetch(`${API}/api/recipes/${encodeURIComponent(name)}/execute`, { method: "POST" });
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (e) { setResult(`Error: ${e}`); }
    setRunning(null);
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <BookMarked size={22} className="text-[var(--color-nexus-accent)]" /> Recipes
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Workflows pre-armados ejecutables</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {recipes.map((r) => (
          <div key={r.name} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 flex flex-col">
            <div className="text-sm font-semibold text-[var(--color-nexus-text)] mb-1">{r.name}</div>
            <p className="text-xs text-[var(--color-nexus-text-sub)] mb-3 flex-1">{r.description}</p>
            {r.steps?.length > 0 && (
              <div className="mb-3 space-y-1">
                {r.steps.slice(0, 4).map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-[10px] text-[var(--color-nexus-muted)]">
                    <span className="w-4 h-4 rounded-full bg-[var(--color-nexus-surface-2)] flex items-center justify-center text-[8px] font-bold shrink-0">{i + 1}</span>
                    <span className="truncate">{s}</span>
                  </div>
                ))}
                {r.steps.length > 4 && <div className="text-[10px] text-[var(--color-nexus-muted)] pl-6">+{r.steps.length - 4} pasos más</div>}
              </div>
            )}
            {r.tags && (
              <div className="flex flex-wrap gap-1 mb-3">
                {r.tags.map((t) => (
                  <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]">{t}</span>
                ))}
              </div>
            )}
            <button onClick={() => execute(r.name)} disabled={running === r.name}
              className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)] hover:text-white disabled:opacity-50 transition-colors">
              {running === r.name ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
              {running === r.name ? "Ejecutando..." : "Ejecutar"}
            </button>
          </div>
        ))}
        {recipes.length === 0 && !loading && (
          <div className="col-span-full text-center py-12 text-sm text-[var(--color-nexus-muted)]">No hay recipes definidos.</div>
        )}
      </div>

      {result && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-2">Resultado</div>
          <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-48 overflow-auto">{result}</pre>
        </div>
      )}
    </div>
  );
}
