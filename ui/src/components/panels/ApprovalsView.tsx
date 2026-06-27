import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { ShieldCheck, RefreshCw, CheckCircle2, XCircle, Clock } from "lucide-react";



interface Approval { id: string; action: string; gem: string; reason: string; status: "pending" | "approved" | "rejected"; created_at: string; risk_level?: string; }

export function ApprovalsView() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`${API}/api/approvals`);
      const data = await res.json();
      setApprovals(Array.isArray(data.approvals) ? data.approvals : Array.isArray(data.pending) ? data.pending : Array.isArray(data) ? data : []);
    } catch { setApprovals([]); }
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); const iv = setInterval(refresh, 5000); return () => clearInterval(iv); }, [refresh]);

  const respond = async (id: string, decision: "approve" | "reject") => {
    await authFetch(`${API}/api/approvals/${id}/respond`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    });
    refresh();
  };

  const pending = approvals.filter((a) => a.status === "pending");
  const resolved = approvals.filter((a) => a.status !== "pending");

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <ShieldCheck size={22} className="text-[var(--color-nexus-accent)]" /> Aprobaciones
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Acciones que requieren autorización humana</p>
        </div>
        <div className="flex items-center gap-2">
          {pending.length > 0 && (
            <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[var(--color-nexus-busy)]/15 text-[var(--color-nexus-busy)] animate-pulse">
              {pending.length} pendientes
            </span>
          )}
          <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Pending */}
      {pending.length > 0 && (
        <div className="space-y-3">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">Pendientes</div>
          {pending.map((a) => (
            <div key={a.id} className="bg-[var(--color-nexus-surface)] border-2 border-[var(--color-nexus-busy)] rounded-xl p-4">
              <div className="flex items-start gap-3">
                <Clock size={16} className="text-[var(--color-nexus-busy)] shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-[var(--color-nexus-text)]">{a.action}</div>
                  <div className="text-xs text-[var(--color-nexus-text-sub)] mt-0.5">{a.reason}</div>
                  <div className="flex items-center gap-2 mt-1 text-[10px] text-[var(--color-nexus-muted)] font-mono">
                    <span>gema: {a.gem}</span>
                    {a.risk_level && <span className="text-[var(--color-nexus-error)]">riesgo: {a.risk_level}</span>}
                    <span>{new Date(a.created_at).toLocaleString("es")}</span>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => respond(a.id, "approve")}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-online)]/15 text-[var(--color-nexus-online)] hover:bg-[var(--color-nexus-online)] hover:text-white transition-colors">
                    <CheckCircle2 size={12} /> Aprobar
                  </button>
                  <button onClick={() => respond(a.id, "reject")}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-error)]/15 text-[var(--color-nexus-error)] hover:bg-[var(--color-nexus-error)] hover:text-white transition-colors">
                    <XCircle size={12} /> Rechazar
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Resolved */}
      {resolved.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">Historial</div>
          {resolved.slice(0, 20).map((a) => (
            <div key={a.id} className="flex items-center gap-3 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-2.5">
              {a.status === "approved" ? <CheckCircle2 size={14} className="text-[var(--color-nexus-online)]" /> : <XCircle size={14} className="text-[var(--color-nexus-error)]" />}
              <div className="flex-1 min-w-0">
                <div className="text-xs text-[var(--color-nexus-text)] truncate">{a.action}</div>
                <div className="text-[10px] text-[var(--color-nexus-muted)] font-mono">{a.gem} · {new Date(a.created_at).toLocaleString("es")}</div>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full ${a.status === "approved" ? "bg-[var(--color-nexus-online)]/15 text-[var(--color-nexus-online)]" : "bg-[var(--color-nexus-error)]/15 text-[var(--color-nexus-error)]"}`}>
                {a.status}
              </span>
            </div>
          ))}
        </div>
      )}

      {approvals.length === 0 && !loading && (
        <div className="text-center py-16 text-sm text-[var(--color-nexus-muted)]">No hay aprobaciones pendientes ni historial.</div>
      )}
    </div>
  );
}
