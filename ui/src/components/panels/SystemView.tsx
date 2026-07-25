import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Activity, RefreshCw, Cpu, HardDrive, MemoryStick, GitBranch, Wrench } from "lucide-react";



export function SystemView() {
  const [stats, setStats] = useState<any>(null);
  const [memHealth, setMemHealth] = useState<any>(null);
  const [toolMon, setToolMon] = useState<any>(null);
  const [graph, setGraph] = useState<any>(null);
  const [checkpoints, setCheckpoints] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [st, mh, tm, gr, cp] = await Promise.all([
        authFetch(`${API}/api/system/stats`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/memory/health`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/tools/monitor`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/graph/status`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/checkpoints`).then(r => r.json()).catch(() => null),
      ]);
      setStats(st); setMemHealth(mh); setToolMon(tm); setGraph(gr);
      setCheckpoints(cp?.checkpoints || cp || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const MetricCard = ({ label, value, icon, color = "var(--color-nexus-accent)" }: { label: string; value: string | number; icon: React.ReactNode; color?: string }) => (
    <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 flex items-center gap-3">
      <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${color}15` }}>
        {icon}
      </div>
      <div>
        <div className="text-lg font-bold text-[var(--color-nexus-text)]">{value}</div>
        <div className="text-[10px] text-[var(--color-nexus-muted)] uppercase tracking-wider">{label}</div>
      </div>
    </div>
  );

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Activity size={22} className="text-[var(--color-nexus-accent)]" /> System Overview
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Métricas, salud de memoria, herramientas y grafos</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard label="CPU" value={stats.cpu_percent ? `${stats.cpu_percent}%` : typeof stats.cpu === "object" ? JSON.stringify(stats.cpu) : (stats.cpu || "N/A")} icon={<Cpu size={18} style={{ color: "var(--color-nexus-accent)" }} />} />
          <MetricCard label="RAM" value={stats.memory_percent ? `${stats.memory_percent}%` : (stats.memory_used || "N/A")} icon={<MemoryStick size={18} style={{ color: "#00ff88" }} />} color="#00ff88" />
          <MetricCard label="Disco" value={stats.disk_percent ? `${stats.disk_percent}%` : (stats.disk_used || "N/A")} icon={<HardDrive size={18} style={{ color: "#ff6b00" }} />} color="#ff6b00" />
          <MetricCard label="Uptime" value={stats.uptime || (stats.uptime_seconds ? `${Math.floor((stats.uptime_seconds || 0) / 60)}m` : "N/A")} icon={<Activity size={18} style={{ color: "#a78bfa" }} />} color="#a78bfa" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <MemoryStick size={14} className="text-[var(--color-nexus-online)]" />
            <span className="text-sm font-semibold text-[var(--color-nexus-text)]">Memory Health</span>
          </div>
          {memHealth ? (
            <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-40 overflow-auto">{JSON.stringify(memHealth, null, 2)}</pre>
          ) : <div className="text-xs text-[var(--color-nexus-muted)]">Cargando...</div>}
        </div>

        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Wrench size={14} className="text-[var(--color-nexus-accent)]" />
            <span className="text-sm font-semibold text-[var(--color-nexus-text)]">Tool Monitor</span>
          </div>
          {toolMon ? (
            <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-40 overflow-auto">{JSON.stringify(toolMon, null, 2)}</pre>
          ) : <div className="text-xs text-[var(--color-nexus-muted)]">Cargando...</div>}
        </div>

        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <GitBranch size={14} className="text-[#a78bfa]" />
            <span className="text-sm font-semibold text-[var(--color-nexus-text)]">Graph Evolution</span>
          </div>
          {graph ? (
            <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-40 overflow-auto">{JSON.stringify(graph, null, 2)}</pre>
          ) : <div className="text-xs text-[var(--color-nexus-muted)]">Cargando...</div>}
        </div>

        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <HardDrive size={14} className="text-[#ff6b00]" />
            <span className="text-sm font-semibold text-[var(--color-nexus-text)]">Checkpoints ({checkpoints.length})</span>
          </div>
          {checkpoints.length > 0 ? (
            <div className="space-y-1.5 max-h-40 overflow-auto">
              {checkpoints.slice(0, 10).map((cp: any, i: number) => (
                <div key={i} className="flex justify-between text-[11px]">
                  <span className="text-[var(--color-nexus-text-sub)] truncate">{cp.run_id || cp.id || `checkpoint-${i}`}</span>
                  <span className="text-[var(--color-nexus-muted)] font-mono shrink-0 ml-2">{cp.step || cp.status || ""}</span>
                </div>
              ))}
            </div>
          ) : <div className="text-xs text-[var(--color-nexus-muted)]">Sin checkpoints</div>}
        </div>
      </div>
    </div>
  );
}
