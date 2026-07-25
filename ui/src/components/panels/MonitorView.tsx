import { useState, useEffect, useCallback, ReactNode } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Activity, RefreshCw, Heart, Brain, Mic, Database, Boxes } from "lucide-react";

interface Panel {
  key: string; title: string; icon: any; url: string;
  render: (d: any) => ReactNode;
}

const PANELS: Panel[] = [
  {
    key: "dmn", title: "DMN Reflection", icon: Brain,
    url: "/api/dmn/stats",
    render: (d) => (
      <div className="text-xs space-y-1">
        <div>running: <span className="font-mono text-[var(--color-nexus-accent)]">{String(d.running)}</span> · interval {d.interval_s}s</div>
        <div className="text-[var(--color-nexus-muted)]">ticks={d.stats?.ticks} · candidates={d.stats?.candidates} · spoken={d.stats?.spoken} · logged={d.stats?.logged} · dropped={d.stats?.dropped}</div>
      </div>
    ),
  },
  {
    key: "mcp", title: "MCP Servers", icon: Database,
    url: "/api/mcp/health",
    render: (d) => (
      <div className="text-xs space-y-1">
        <div>total {d.total} · alive {d.alive} · connected {d.connected}</div>
        <div className="grid grid-cols-2 gap-1 mt-2 max-h-32 overflow-y-auto">
          {Object.entries(d.servers || {}).map(([n, s]: any) => (
            <span key={n} className={`px-2 py-0.5 rounded font-mono text-[10px] ${s.connected ? "bg-[var(--color-nexus-online)]/15 text-[var(--color-nexus-online)]" : "bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]"}`}>
              {n} {s.connected ? "UP" : "—"}
            </span>
          ))}
        </div>
      </div>
    ),
  },
  {
    key: "workers", title: "Stalled Workers", icon: Activity,
    url: "/api/workers/stalled",
    render: (d) => (
      <div className="text-xs space-y-1">
        <div>stalled: <span className="font-mono">{d.stalled_count ?? 0}</span> / threshold {d.threshold_minutes}min</div>
        {(d.stalled || []).map((w: any) => (
          <div key={w.name} className="text-[var(--color-nexus-error)]">⚠ {w.name}: {w.minutes_since}min</div>
        ))}
        {(!d.stalled || d.stalled.length === 0) && <div className="text-[var(--color-nexus-online)]">✓ todos OK</div>}
      </div>
    ),
  },
  {
    key: "voice", title: "Voice Gate", icon: Mic,
    url: "/api/voice/gate/stats",
    render: (d) => (
      <div className="text-xs space-y-1">
        <div>thresholds: speak ≥{d.speak_threshold} · log ≥{d.log_threshold}</div>
        <div className="text-[var(--color-nexus-muted)]">scored={d.stats?.scored} · spoken={d.stats?.spoken} · logged={d.stats?.logged} · dropped={d.stats?.dropped}</div>
      </div>
    ),
  },
  {
    key: "events", title: "Event Bus", icon: Heart,
    url: "/api/events/stats",
    render: (d) => (
      <div className="text-xs space-y-1">
        <div>emitted: <span className="font-mono">{d.events_emitted}</span> · subs {d.subscribers} · persist {String(d.persist_enabled)}</div>
        {d.subscriber_labels?.length > 0 && (
          <div className="text-[10px] font-mono text-[var(--color-nexus-muted)]">{d.subscriber_labels.join(", ")}</div>
        )}
      </div>
    ),
  },
  {
    key: "sbom", title: "SBOM", icon: Boxes,
    url: "/api/sbom",
    render: (d) => {
      const s = d.summary || {};
      return (
        <div className="text-xs space-y-1">
          <div>gemas {s.gemas} · MCP {s.mcp_servers} · brain {s.brain_modules_wired}/6 · ollama {String(s.ollama_reachable)}</div>
          <div className="text-[var(--color-nexus-muted)]">auth {String(s.auth_on)} · caps_enforced {String(s.caps_enforced)}</div>
        </div>
      );
    },
  },
];

export function MonitorView() {
  const [data, setData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    const results: Record<string, any> = {};
    await Promise.all(PANELS.map(async (p) => {
      try {
        const r = await authFetch(`${API}${p.url}`);
        results[p.key] = await r.json();
      } catch { results[p.key] = { error: "fetch failed" }; }
    }));
    setData(results);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 10000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Activity size={22} className="text-[var(--color-nexus-accent)]" /> Monitor
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">DMN · MCP · Workers · Voice · Events · SBOM (auto-refresh 10s)</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {PANELS.map(p => {
          const Icon = p.icon;
          const d = data[p.key];
          return (
            <div key={p.key} className="rounded-xl border border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)] p-4">
              <div className="flex items-center gap-2 mb-3">
                <Icon size={14} className="text-[var(--color-nexus-accent)]" />
                <h3 className="text-sm font-semibold">{p.title}</h3>
                <span className="ml-auto text-[10px] text-[var(--color-nexus-muted)] font-mono">{p.url}</span>
              </div>
              {d ? (
                d.error ? (
                  <div className="text-xs text-[var(--color-nexus-error)]">{d.error}</div>
                ) : p.render(d)
              ) : (
                <div className="text-xs text-[var(--color-nexus-muted)]">cargando...</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
