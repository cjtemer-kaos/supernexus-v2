import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Terminal, Play, Plus, RefreshCw, Trash2, Loader2 } from "lucide-react";



interface Command { name: string; description: string; script?: string; tags?: string[]; }

export function CommandsView() {
  const [commands, setCommands] = useState<Command[]>([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newScript, setNewScript] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/commands`);
      const data = await res.json();
      setCommands(data.commands || data || []);
    } catch { setCommands([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const execute = async (name: string) => {
    setRunning(name); setResult(null);
    try {
      const res = await authFetch(`${API}/api/commands/${encodeURIComponent(name)}/execute`, { method: "POST" });
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
    } catch (e) { setResult(`Error: ${e}`); }
    setRunning(null);
  };

  const create = async () => {
    if (!newName.trim()) return;
    await authFetch(`${API}/api/commands`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName, description: newDesc, script: newScript }),
    });
    setNewName(""); setNewDesc(""); setNewScript(""); setShowAdd(false);
    refresh();
  };

  const remove = async (name: string) => {
    await authFetch(`${API}/api/commands/${encodeURIComponent(name)}`, { method: "DELETE" });
    refresh();
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Terminal size={22} className="text-[var(--color-nexus-accent)]" /> Custom Commands
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Comandos personalizados del sistema</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowAdd(!showAdd)} className="p-2 rounded-lg bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)] hover:text-white transition-colors">
            <Plus size={14} />
          </button>
          <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
          <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Nombre del comando"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] outline-none" />
          <input value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Descripción"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none" />
          <textarea value={newScript} onChange={e => setNewScript(e.target.value)} placeholder="Script / instrucciones..." rows={3}
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs font-mono text-[var(--color-nexus-text)] outline-none resize-none" />
          <button onClick={create} className="px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white">Crear</button>
        </div>
      )}

      <div className="space-y-2">
        {commands.map(c => (
          <div key={c.name} className="flex items-center gap-4 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3">
            <Terminal size={14} className="text-[var(--color-nexus-accent)] shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-[var(--color-nexus-text)]">{c.name}</div>
              <div className="text-[10px] text-[var(--color-nexus-muted)] mt-0.5">{c.description}</div>
            </div>
            <button onClick={() => execute(c.name)} disabled={running === c.name}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)] hover:text-white disabled:opacity-50 transition-colors">
              {running === c.name ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
              {running === c.name ? "..." : "Ejecutar"}
            </button>
            <button onClick={() => remove(c.name)} className="p-1.5 rounded-lg text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-error)] transition-colors">
              <Trash2 size={12} />
            </button>
          </div>
        ))}
        {commands.length === 0 && !loading && <div className="text-center py-12 text-sm text-[var(--color-nexus-muted)]">Sin comandos personalizados</div>}
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
