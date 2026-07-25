import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Stethoscope, Play, RefreshCw, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";



interface DiagItem { check: string; status: "ok" | "warning" | "error"; message: string; }

const ICONS = { ok: CheckCircle2, warning: AlertTriangle, error: XCircle };
const COLORS = { ok: "var(--color-nexus-online)", warning: "var(--color-nexus-busy)", error: "var(--color-nexus-error)" };

export function DoctorView() {
  const [results, setResults] = useState<DiagItem[]>([]);
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<string | null>(null);

  // Normalize new live diagnostic shape (commit 8/35/37) to legacy DiagItem[]
  const normalizeChecks = (data: any): DiagItem[] => {
    if (Array.isArray(data?.results)) return data.results;
    if (data?.checks && typeof data.checks === "object") {
      const statusMap: Record<string, "ok"|"warning"|"error"> = {
        ok: "ok", warn: "warning", fail: "error"
      };
      return Object.entries(data.checks).map(([name, v]: [string, any]) => ({
        check: name,
        status: statusMap[v?.status] || "warning",
        message: v?.detail || JSON.stringify(v?.data || {}).slice(0, 120),
      }));
    }
    return [];
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await authFetch(`${API}/api/doctor`);
      const data = await res.json();
      const items = normalizeChecks(data);
      if (items.length) setResults(items);
      if (data.last_run || data.generated_at) setLastRun(data.last_run || data.generated_at);
    } catch {}
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  const runDoctor = async () => {
    setRunning(true);
    try {
      const res = await authFetch(`${API}/api/doctor/run`, { method: "POST" });
      const data = await res.json();
      setResults(normalizeChecks(data));
      setLastRun(new Date().toISOString());
    } catch {}
    setRunning(false);
  };

  const okCount = results.filter((r) => r.status === "ok").length;
  const warnCount = results.filter((r) => r.status === "warning").length;
  const errCount = results.filter((r) => r.status === "error").length;

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Stethoscope size={22} className="text-[var(--color-nexus-accent)]" /> Doctor
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Diagnóstico completo del sistema</p>
        </div>
        <button onClick={runDoctor} disabled={running}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-50 transition-colors">
          {running ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {running ? "Ejecutando..." : "Ejecutar diagnóstico"}
        </button>
      </div>

      {results.length > 0 && (
        <>
          <div className="flex gap-4 text-sm">
            <span className="flex items-center gap-1 text-[var(--color-nexus-online)]"><CheckCircle2 size={14} /> {okCount} OK</span>
            <span className="flex items-center gap-1 text-[var(--color-nexus-busy)]"><AlertTriangle size={14} /> {warnCount} Warnings</span>
            <span className="flex items-center gap-1 text-[var(--color-nexus-error)]"><XCircle size={14} /> {errCount} Errores</span>
            {lastRun && <span className="text-[10px] text-[var(--color-nexus-muted)] font-mono ml-auto">último: {new Date(lastRun).toLocaleString("es")}</span>}
          </div>

          <div className="space-y-2">
            {results.map((r, i) => {
              const Icon = ICONS[r.status];
              return (
                <div key={i} className="flex items-start gap-3 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3">
                  <Icon size={16} style={{ color: COLORS[r.status] }} className="shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[var(--color-nexus-text)]">{r.check}</div>
                    <div className="text-xs text-[var(--color-nexus-text-sub)] mt-0.5">{r.message}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {results.length === 0 && !running && (
        <div className="text-center py-16 text-sm text-[var(--color-nexus-muted)]">
          Pulsa "Ejecutar diagnóstico" para analizar el estado del sistema.
        </div>
      )}
    </div>
  );
}
