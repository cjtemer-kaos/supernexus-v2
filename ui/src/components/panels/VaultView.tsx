import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Lock, Search, Plus, RefreshCw, FileText } from "lucide-react";



interface VaultItem { id: string; title: string; content: string; tags?: string[]; created_at?: string; }

export function VaultView() {
  const [items, setItems] = useState<VaultItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [newTags, setNewTags] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const url = query.trim() ? `${API}/api/vault/search?q=${encodeURIComponent(query)}` : `${API}/api/vault`;
      const res = await authFetch(url);
      const data = await res.json();
      setItems(Array.isArray(data.items) ? data.items : Array.isArray(data.results) ? data.results : Array.isArray(data.notes) ? data.notes : Array.isArray(data) ? data : []);
    } catch { setItems([]); }
    setLoading(false);
  }, [query]);

  useEffect(() => { refresh(); }, [refresh]);

  const addItem = async () => {
    if (!newTitle.trim()) return;
    await authFetch(`${API}/api/vault`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle, content: newContent, tags: newTags.split(",").map(t => t.trim()).filter(Boolean) }),
    });
    setNewTitle(""); setNewContent(""); setNewTags(""); setShowAdd(false);
    refresh();
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Lock size={22} className="text-[var(--color-nexus-accent)]" /> Knowledge Vault
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Almacén seguro de conocimiento persistente</p>
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

      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-nexus-muted)]" />
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar en el vault..."
          className="w-full pl-9 pr-4 py-2.5 rounded-xl bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] text-sm text-[var(--color-nexus-text)] outline-none focus:border-[var(--color-nexus-accent)]" />
      </div>

      {showAdd && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
          <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Título"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] outline-none" />
          <textarea value={newContent} onChange={e => setNewContent(e.target.value)} placeholder="Contenido..." rows={4}
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] outline-none resize-none" />
          <input value={newTags} onChange={e => setNewTags(e.target.value)} placeholder="Tags (separados por coma)"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none" />
          <button onClick={addItem} className="px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] transition-colors">
            Guardar en Vault
          </button>
        </div>
      )}

      <div className="space-y-2">
        {items.map(item => (
          <div key={item.id} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3 cursor-pointer hover:border-[var(--color-nexus-accent)]/30 transition-colors"
            onClick={() => setExpanded(expanded === item.id ? null : item.id)}>
            <div className="flex items-center gap-3">
              <FileText size={14} className="text-[var(--color-nexus-accent)] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[var(--color-nexus-text)] truncate">{item.title}</div>
                <div className="flex gap-2 mt-0.5">
                  {item.created_at && <span className="text-[10px] text-[var(--color-nexus-muted)] font-mono">{new Date(item.created_at).toLocaleString("es")}</span>}
                  {item.tags?.map(t => <span key={t} className="text-[9px] px-1.5 py-0.5 rounded-full bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]">{t}</span>)}
                </div>
              </div>
            </div>
            {expanded === item.id && (
              <pre className="mt-3 text-xs text-[var(--color-nexus-text-sub)] font-mono bg-[var(--color-nexus-bg)] rounded-lg p-3 max-h-48 overflow-auto whitespace-pre-wrap">{item.content}</pre>
            )}
          </div>
        ))}
        {items.length === 0 && !loading && <div className="text-center py-12 text-sm text-[var(--color-nexus-muted)]">Vault vacío</div>}
      </div>
    </div>
  );
}
