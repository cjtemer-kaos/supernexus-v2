import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Coins, RefreshCw } from "lucide-react";



interface BudgetData { total_limit: number; used: number; remaining: number; period: string; per_gem?: Record<string, number>; }
interface TokenReport { total_tokens: number; by_model: Record<string, number>; by_gem: Record<string, number>; estimated_cost: number; }

function Bar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="h-2 w-full rounded-full bg-[var(--color-nexus-surface-2)] overflow-hidden">
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(pct, 100)}%`, backgroundColor: color }} />
    </div>
  );
}

export function BudgetView() {
  const [budget, setBudget] = useState<BudgetData | null>(null);
  const [report, setReport] = useState<TokenReport | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      // Combined: legacy /api/budget + new /api/budget/all (sessions catalog)
      const [bRes, rRes, allRes] = await Promise.all([
        authFetch(`${API}/api/budget`),
        authFetch(`${API}/api/token/report`),
        authFetch(`${API}/api/budget/all`).catch(() => null),
      ]);
      setBudget(await bRes.json());
      setReport(await rRes.json());
      // New: per-session breakdown (commits 25/28)
      if (allRes && allRes.ok) {
        try {
          const all = await allRes.json();
          (window as any).__nexusBudgetAll = all;  // exposed for SessionsView
        } catch {}
      }
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const usedPct = budget ? (budget.used / (budget.total_limit || 1)) * 100 : 0;
  const barColor = usedPct < 50 ? "var(--color-nexus-online)" : usedPct < 80 ? "var(--color-nexus-busy)" : "var(--color-nexus-error)";

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Coins size={22} className="text-[var(--color-nexus-accent)]" /> Token Budget
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Consumo de tokens y control de gasto</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {budget && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[var(--color-nexus-text)]">Presupuesto {budget.period}</span>
            <span className="text-sm font-bold text-[var(--color-nexus-text)]">{budget.used?.toLocaleString()} / {budget.total_limit?.toLocaleString()}</span>
          </div>
          <Bar pct={usedPct} color={barColor} />
          <div className="flex justify-between text-[10px] text-[var(--color-nexus-muted)]">
            <span>{usedPct.toFixed(1)}% usado</span>
            <span>{budget.remaining?.toLocaleString()} restantes</span>
          </div>
        </div>
      )}

      {report && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* By model */}
          <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
            <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-3">Por Modelo</div>
            <div className="space-y-2">
              {Object.entries(report.by_model || {}).sort(([,a],[,b]) => b - a).map(([model, tokens]) => (
                <div key={model} className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-nexus-text)] font-mono truncate">{model}</span>
                  <span className="text-xs font-medium text-[var(--color-nexus-text-sub)]">{tokens.toLocaleString()}</span>
                </div>
              ))}
              {Object.keys(report.by_model || {}).length === 0 && <div className="text-xs text-[var(--color-nexus-muted)]">Sin datos</div>}
            </div>
          </div>

          {/* By gem */}
          <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
            <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-3">Por Gema</div>
            <div className="space-y-2">
              {Object.entries(report.by_gem || {}).sort(([,a],[,b]) => b - a).map(([gem, tokens]) => (
                <div key={gem} className="flex items-center justify-between">
                  <span className="text-xs text-[var(--color-nexus-text)] capitalize">{gem}</span>
                  <span className="text-xs font-medium text-[var(--color-nexus-text-sub)]">{tokens.toLocaleString()}</span>
                </div>
              ))}
              {Object.keys(report.by_gem || {}).length === 0 && <div className="text-xs text-[var(--color-nexus-muted)]">Sin datos</div>}
            </div>
          </div>
        </div>
      )}

      {report?.estimated_cost !== undefined && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 text-center">
          <div className="text-xs text-[var(--color-nexus-muted)] mb-1">Costo estimado</div>
          <div className="text-2xl font-bold text-[var(--color-nexus-accent)]">${report.estimated_cost.toFixed(4)}</div>
        </div>
      )}
    </div>
  );
}
