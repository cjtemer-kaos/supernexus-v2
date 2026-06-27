import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Network, RefreshCw, Send, Wifi, WifiOff } from "lucide-react";



interface HiveNode { id: string; name: string; status: string; ip?: string; last_seen?: string; models?: string[]; }

export function HiveView() {
  const [nodes, setNodes] = useState<HiveNode[]>([]);
  const [_status, setStatus] = useState<any>(null);
  const [cmd, setCmd] = useState("");
  const [target, setTarget] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [nRes, sRes] = await Promise.all([
        authFetch(`${API}/api/hive/nodes`),
        authFetch(`${API}/api/hive/status`),
      ]);
      const nData = await nRes.json();
      const raw = nData.nodes || nData;
      setNodes(Array.isArray(raw) ? raw : typeof raw === "object" && raw !== null ? Object.entries(raw).map(([k, v]: [string, any]) => ({ id: k, name: v.name || k, status: v.status || "unknown", ip: v.host || v.ip, models: v.models, last_seen: v.last_seen, ...v })) : []);
      setStatus(await sRes.json());
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); const iv = setInterval(refresh, 10000); return () => clearInterval(iv); }, [refresh]);

  const sendCmd = async () => {
    if (!cmd.trim()) return;
    try {
      const res = await authFetch(`${API}/api/hive/send`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, target: target || undefined }),
      });
      const data = await res.json();
      setResult(JSON.stringify(data, null, 2));
      setCmd("");
    } catch (e) { setResult(`Error: ${e}`); }
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <Network size={22} className="text-[var(--color-nexus-accent)]" /> NexusHive
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Nodos de la colmena y control remoto</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Nodes grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {nodes.map((n) => (
          <div key={n.id} className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              {n.status === "online" ? <Wifi size={14} className="text-[var(--color-nexus-online)]" /> : <WifiOff size={14} className="text-[var(--color-nexus-error)]" />}
              <span className="text-sm font-semibold text-[var(--color-nexus-text)]">{n.name || n.id}</span>
              <span className={`ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium ${n.status === "online" ? "bg-[var(--color-nexus-online)]/15 text-[var(--color-nexus-online)]" : "bg-[var(--color-nexus-error)]/15 text-[var(--color-nexus-error)]"}`}>
                {n.status}
              </span>
            </div>
            {n.ip && <div className="text-[10px] font-mono text-[var(--color-nexus-muted)]">{n.ip}</div>}
            {n.models && <div className="text-[10px] text-[var(--color-nexus-text-sub)] mt-1">{n.models.join(", ")}</div>}
            {n.last_seen && <div className="text-[10px] text-[var(--color-nexus-muted)] mt-1">visto: {new Date(n.last_seen).toLocaleString("es")}</div>}
          </div>
        ))}
        {nodes.length === 0 && <div className="col-span-full text-center py-8 text-sm text-[var(--color-nexus-muted)]">Sin nodos detectados</div>}
      </div>

      {/* Send command */}
      <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
        <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">Enviar comando a la colmena</div>
        <div className="flex gap-2">
          <input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Target (vacío=broadcast)"
            className="w-40 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none focus:border-[var(--color-nexus-accent)]" />
          <input value={cmd} onChange={(e) => setCmd(e.target.value)} onKeyDown={(e) => e.key === "Enter" && sendCmd()} placeholder="Comando..."
            className="flex-1 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none focus:border-[var(--color-nexus-accent)]" />
          <button onClick={sendCmd} className="p-2 rounded-lg bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] transition-colors">
            <Send size={14} />
          </button>
        </div>
        {result && (
          <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] bg-[var(--color-nexus-bg)] rounded-lg p-3 max-h-40 overflow-auto">{result}</pre>
        )}
      </div>
    </div>
  );
}
