import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { GitBranch, Play, RefreshCw, ChevronDown, ChevronRight, CheckCircle2, Clock, AlertCircle, Loader2 } from "lucide-react";



interface DAGNode { id: string; name: string; status: string; depends_on: string[]; result?: string; }
interface DAG { id: string; goal: string; status: string; created_at: string; nodes: DAGNode[]; }

const STATUS_ICON: Record<string, typeof CheckCircle2> = { done: CheckCircle2, running: Loader2, pending: Clock, error: AlertCircle };
const STATUS_COLOR: Record<string, string> = { done: "var(--color-nexus-online)", running: "var(--color-nexus-accent)", pending: "var(--color-nexus-muted)", error: "var(--color-nexus-error)" };

export function DAGView() {
  const [dags, setDags] = useState<DAG[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [goal, setGoal] = useState("");
  const [loading, setLoading] = useState(false);
  const [decomposing, setDecomposing] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/dag`);
      const data = await res.json();
      setDags(Array.isArray(data.dags) ? data.dags : Array.isArray(data.runs) ? data.runs : Array.isArray(data) ? data : []);
    } catch { setDags([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const decompose = async () => {
    if (!goal.trim()) return;
    setDecomposing(true);
    try {
      const res = await authFetch(`${API}/api/dag/decompose`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: goal.trim() }),
      });
      const data = await res.json();
      if (data.id) setExpanded((p) => new Set(p).add(data.id));
      setGoal("");
      refresh();
    } catch {}
    setDecomposing(false);
  };

  const executeDag = async (id: string) => {
    await authFetch(`${API}/api/dag/${id}/execute`, { method: "POST" });
    setTimeout(refresh, 1000);
  };

  const toggle = (id: string) => {
    setExpanded((p) => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <GitBranch size={22} className="text-[var(--color-nexus-accent)]" /> Goal → DAG
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Descompone objetivos en grafos de tareas ejecutables</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Decompose input */}
      <div className="flex gap-2">
        <input value={goal} onChange={(e) => setGoal(e.target.value)} onKeyDown={(e) => e.key === "Enter" && decompose()}
          placeholder="Describe un objetivo para descomponer en tareas..."
          className="flex-1 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3 text-sm text-[var(--color-nexus-text)] placeholder:text-[var(--color-nexus-muted)] outline-none focus:border-[var(--color-nexus-accent)]" />
        <button onClick={decompose} disabled={!goal.trim() || decomposing}
          className="flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-30 transition-colors">
          {decomposing ? <Loader2 size={14} className="animate-spin" /> : <GitBranch size={14} />}
          Descomponer
        </button>
      </div>

      {/* DAG list */}
      <div className="space-y-3">
        {dags.length === 0 && !loading && (
          <div className="text-center py-12 text-sm text-[var(--color-nexus-muted)]">No hay DAGs creados. Escribe un objetivo arriba.</div>
        )}
        {dags.map((dag) => (
          <div key={dag.id} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl overflow-hidden">
            <div className="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-[var(--color-nexus-surface-2)]" onClick={() => toggle(dag.id)}>
              {expanded.has(dag.id) ? <ChevronDown size={14} className="text-[var(--color-nexus-muted)]" /> : <ChevronRight size={14} className="text-[var(--color-nexus-muted)]" />}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[var(--color-nexus-text)] truncate">{dag.goal}</div>
                <div className="text-[10px] text-[var(--color-nexus-muted)] font-mono">{dag.id} · {dag.nodes?.length || 0} nodos · {dag.status}</div>
              </div>
              <button onClick={(e) => { e.stopPropagation(); executeDag(dag.id); }}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)] hover:text-white transition-colors">
                <Play size={11} /> Ejecutar
              </button>
            </div>
            {expanded.has(dag.id) && dag.nodes && (
              <div className="border-t border-[var(--color-nexus-border)] px-4 py-3 space-y-2">
                {dag.nodes.map((node) => {
                  const Icon = STATUS_ICON[node.status] || Clock;
                  return (
                    <div key={node.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[var(--color-nexus-bg)]">
                      <Icon size={14} style={{ color: STATUS_COLOR[node.status] || STATUS_COLOR.pending }} className={node.status === "running" ? "animate-spin" : ""} />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium text-[var(--color-nexus-text)]">{node.name}</div>
                        {node.depends_on?.length > 0 && <div className="text-[10px] text-[var(--color-nexus-muted)]">depende de: {node.depends_on.join(", ")}</div>}
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full" style={{ backgroundColor: `${STATUS_COLOR[node.status] || STATUS_COLOR.pending}15`, color: STATUS_COLOR[node.status] }}>{node.status}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
