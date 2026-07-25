import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Shield, RefreshCw, AlertTriangle, CheckCircle2, XCircle, Play } from "lucide-react";



export function GuardianView() {
  const [guardian, setGuardian] = useState<any>(null);
  const [safety, setSafety] = useState<any>(null);
  const [guardrails, setGuardrails] = useState<any>(null);
  const [risk, setRisk] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [auditResult, setAuditResult] = useState<string | null>(null);
  const [riskInput, setRiskInput] = useState("");
  const [riskResult, setRiskResult] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [g, s, gr, r] = await Promise.all([
        authFetch(`${API}/api/guardian/status`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/safety/status`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/guardrails/status`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/risk`).then(r => r.json()).catch(() => null),
      ]);
      setGuardian(g); setSafety(s); setGuardrails(gr); setRisk(r);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const runAudit = async () => {
    const res = await authFetch(`${API}/api/guardian/audit`, { method: "POST" });
    const data = await res.json();
    setAuditResult(JSON.stringify(data, null, 2));
  };

  const assessRisk = async () => {
    if (!riskInput.trim()) return;
    const res = await authFetch(`${API}/api/risk/assess`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: riskInput }),
    });
    const data = await res.json();
    setRiskResult(JSON.stringify(data, null, 2));
  };

  const StatusCard = ({ title, data, icon }: { title: string; data: any; icon: React.ReactNode }) => (
    <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <span className="text-sm font-semibold text-[var(--color-nexus-text)]">{title}</span>
      </div>
      {data ? (
        <div className="space-y-1.5">
          {Object.entries(data).slice(0, 6).map(([k, v]) => (
            <div key={k} className="flex justify-between text-[11px]">
              <span className="text-[var(--color-nexus-muted)]">{k}</span>
              <span className="text-[var(--color-nexus-text)] font-mono">
                {typeof v === "boolean" ? (v ? <CheckCircle2 size={12} className="text-[var(--color-nexus-online)]" /> : <XCircle size={12} className="text-[var(--color-nexus-error)]" />) : String(v)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-xs text-[var(--color-nexus-muted)]">No disponible</div>
      )}
    </div>
  );

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Shield size={22} className="text-[var(--color-nexus-accent)]" /> Guardian & Security
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Seguridad, guardrails, evaluación de riesgo</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard title="Guardian" data={guardian} icon={<Shield size={14} className="text-[var(--color-nexus-accent)]" />} />
        <StatusCard title="Safety" data={safety} icon={<CheckCircle2 size={14} className="text-[var(--color-nexus-online)]" />} />
        <StatusCard title="Guardrails" data={guardrails} icon={<AlertTriangle size={14} className="text-yellow-500" />} />
        <StatusCard title="Risk Summary" data={risk} icon={<AlertTriangle size={14} className="text-[var(--color-nexus-error)]" />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">Auditoría de seguridad</div>
          <button onClick={runAudit} className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)] hover:text-white transition-colors">
            <Play size={12} /> Ejecutar auditoría
          </button>
          {auditResult && <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] bg-[var(--color-nexus-bg)] rounded-lg p-3 max-h-40 overflow-auto">{auditResult}</pre>}
        </div>

        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">Evaluar riesgo</div>
          <div className="flex gap-2">
            <input value={riskInput} onChange={e => setRiskInput(e.target.value)} placeholder="Acción a evaluar..."
              className="flex-1 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none" />
            <button onClick={assessRisk} className="px-3 py-2 rounded-lg text-xs bg-[var(--color-nexus-accent)] text-white">Evaluar</button>
          </div>
          {riskResult && <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] bg-[var(--color-nexus-bg)] rounded-lg p-3 max-h-40 overflow-auto">{riskResult}</pre>}
        </div>
      </div>
    </div>
  );
}
