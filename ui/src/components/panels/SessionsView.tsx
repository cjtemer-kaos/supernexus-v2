import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { History, Archive, RefreshCw, MessageSquare } from "lucide-react";


interface Session { id: string; created_at: string; message_count: number; last_message?: string; compacted: boolean; tokens_total?: number; }

export function SessionsView() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      // Dual fetch: legacy /api/sessions + new /api/sessions/catalog (commit 27)
      // Catalog merges disk-tracked sessions (L1/L2/L3 logs) + in-memory budgets
      const [legacy, catalog] = await Promise.all([
        authFetch(`${API}/api/sessions`).then(r => r.json()).catch(() => ({})),
        authFetch(`${API}/api/sessions/catalog`).then(r => r.json()).catch(() => ({})),
      ]);
      const legacyList = legacy.sessions || legacy || [];
      const catalogList = (catalog.sessions || []).map((s: any) => ({
        id: s.session_id,
        created_at: s.last_update || s.finished_at || new Date().toISOString(),
        message_count: s.request_count || 0,
        last_message: `${s.summary_status || "?"} | $${s.cost_usd || 0}`,
        compacted: false,
        tokens_total: s.total_tokens || 0,
      }));
      // Merge by id, prefer catalog (richer)
      const seen = new Set();
      const merged: Session[] = [];
      for (const s of [...catalogList, ...legacyList]) {
        if (!s.id || seen.has(s.id)) continue;
        seen.add(s.id); merged.push(s);
      }
      setSessions(merged);
    } catch { setSessions([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const compact = async (id: string) => {
    await authFetch(`${API}/api/sessions/${id}/compact`, { method: "POST" });
    refresh();
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <History size={22} className="text-[var(--color-nexus-accent)]" /> Sesiones
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Historial de conversaciones y compresión de contexto</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="space-y-2">
        {sessions.length === 0 && !loading && (
          <div className="text-center py-12 text-sm text-[var(--color-nexus-muted)]">No hay sesiones registradas.</div>
        )}
        {sessions.map((s) => (
          <div key={s.id} className="flex items-center gap-4 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3">
            <MessageSquare size={16} className="text-[var(--color-nexus-accent)] shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-[var(--color-nexus-text)] truncate">{s.last_message || s.id}</div>
              <div className="flex items-center gap-3 text-[10px] text-[var(--color-nexus-muted)] font-mono mt-0.5">
                <span>{new Date(s.created_at).toLocaleString("es")}</span>
                <span>{s.message_count} msgs</span>
                {s.tokens_total && <span>{s.tokens_total.toLocaleString()} tokens</span>}
                {s.compacted && <span className="text-[var(--color-nexus-online)]">compactada</span>}
              </div>
            </div>
            <button onClick={() => compact(s.id)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-medium bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)] transition-colors">
              <Archive size={11} /> Compactar
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
