import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { StickyNote, Plus, RefreshCw, Edit3 } from "lucide-react";



interface Note { id: string; title?: string; content: string; status?: string; created_at?: string; updated_at?: string; }

export function NotesView() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/notes`);
      const data = await res.json();
      setNotes(data.notes || data || []);
    } catch { setNotes([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const create = async () => {
    if (!newContent.trim()) return;
    await authFetch(`${API}/api/notes`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle, content: newContent }),
    });
    setNewTitle(""); setNewContent(""); setShowAdd(false); refresh();
  };

  const update = async (id: string) => {
    await authFetch(`${API}/api/notes/${id}/update`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: editContent }),
    });
    setEditing(null); refresh();
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <StickyNote size={22} className="text-[var(--color-nexus-accent)]" /> Live Notes
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Notas en tiempo real del sistema</p>
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
          <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Título (opcional)"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] outline-none" />
          <textarea value={newContent} onChange={e => setNewContent(e.target.value)} placeholder="Contenido de la nota..." rows={4}
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-sm text-[var(--color-nexus-text)] outline-none resize-none" />
          <button onClick={create} className="px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white">Crear nota</button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {notes.map(n => (
          <div key={n.id} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 flex flex-col">
            <div className="flex items-start justify-between mb-2">
              <div className="text-sm font-semibold text-[var(--color-nexus-text)]">{n.title || "Sin título"}</div>
              <button onClick={() => { setEditing(n.id); setEditContent(n.content); }} className="p-1 text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)]">
                <Edit3 size={12} />
              </button>
            </div>
            {editing === n.id ? (
              <div className="space-y-2">
                <textarea value={editContent} onChange={e => setEditContent(e.target.value)} rows={3}
                  className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none resize-none" />
                <div className="flex gap-2">
                  <button onClick={() => update(n.id)} className="px-3 py-1 rounded-lg text-[10px] bg-[var(--color-nexus-accent)] text-white">Guardar</button>
                  <button onClick={() => setEditing(null)} className="px-3 py-1 rounded-lg text-[10px] bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">Cancelar</button>
                </div>
              </div>
            ) : (
              <p className="text-xs text-[var(--color-nexus-text-sub)] flex-1 whitespace-pre-wrap">{n.content}</p>
            )}
            <div className="flex gap-3 mt-2 text-[10px] text-[var(--color-nexus-muted)] font-mono">
              {n.status && <span className="px-1.5 py-0.5 rounded-full bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]">{n.status}</span>}
              {n.updated_at && <span>{new Date(n.updated_at).toLocaleString("es")}</span>}
            </div>
          </div>
        ))}
        {notes.length === 0 && !loading && <div className="col-span-full text-center py-12 text-sm text-[var(--color-nexus-muted)]">Sin notas</div>}
      </div>
    </div>
  );
}
