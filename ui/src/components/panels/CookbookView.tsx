import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { ChefHat, Cpu, Download, RefreshCw, HardDrive } from "lucide-react";

interface Model {
  name: string; tier: string; size_gb: number; vram_gb: number; use: string;
  reason?: string;
}
interface Hardware {
  os: string; arch: string; cpu_count: number;
  ram_gb: number; free_disk_gb: number; vram_gb: number; gpu_name?: string;
}
interface ScanData {
  hardware: Hardware; recommended: Model[]; can_run: Model[];
  too_big: Model[]; rationale: string;
}

export function CookbookView() {
  const [data, setData] = useState<ScanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState<string | null>(null);
  const [installLog, setInstallLog] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await authFetch(`${API}/api/cookbook/scan`);
      setData(await r.json());
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const install = async (model: string) => {
    setInstalling(model);
    setInstallLog(l => ({ ...l, [model]: "downloading..." }));
    try {
      const r = await authFetch(`${API}/api/cookbook/install`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      const j = await r.json();
      setInstallLog(l => ({
        ...l, [model]: j.ok
          ? `✓ ${(j.bytes_total / 1e9).toFixed(1)}GB ${j.status || ""}`
          : `✗ ${j.error || "failed"}`,
      }));
    } catch (e: any) {
      setInstallLog(l => ({ ...l, [model]: `✗ ${e}` }));
    }
    setInstalling(null);
  };

  const renderRow = (m: Model, kind: "recommended" | "can_run" | "too_big") => {
    const tone = kind === "recommended"
      ? "border-[var(--color-nexus-accent)]/40 bg-[var(--color-nexus-accent)]/5"
      : kind === "too_big"
        ? "border-[var(--color-nexus-border)] opacity-50"
        : "border-[var(--color-nexus-border)]";
    const log = installLog[m.name];
    return (
      <div key={m.name} className={`flex items-center gap-4 rounded-xl border ${tone} px-4 py-3`}>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-[var(--color-nexus-text)]">{m.name}</div>
          <div className="text-[11px] text-[var(--color-nexus-muted)] mt-0.5">
            <span className="font-mono">{m.tier}</span> · {m.size_gb}GB on disk · ~{m.vram_gb}GB VRAM · {m.use}
            {m.reason && <span className="text-[var(--color-nexus-error)] ml-2">[{m.reason}]</span>}
          </div>
          {log && <div className="text-[10px] font-mono mt-1 text-[var(--color-nexus-text-sub)]">{log}</div>}
        </div>
        {kind !== "too_big" && (
          <button
            onClick={() => install(m.name)}
            disabled={installing === m.name}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)]/10 disabled:opacity-50"
          >
            {installing === m.name
              ? <RefreshCw size={11} className="animate-spin" />
              : <Download size={11} />}
            {installing === m.name ? "..." : "Pull"}
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto space-y-6 animate-nexus-in overflow-y-auto h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-nexus-text)] flex items-center gap-2">
            <ChefHat size={22} className="text-[var(--color-nexus-accent)]" /> Cookbook
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Hardware scan + Ollama model recommender</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {data && (
        <>
          <div className="flex flex-wrap gap-3 text-xs">
            <span className="px-3 py-1.5 rounded-lg bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] flex items-center gap-1.5">
              <Cpu size={12} /> {data.hardware.cpu_count} CPU · {data.hardware.ram_gb}GB RAM
            </span>
            <span className="px-3 py-1.5 rounded-lg bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)]">
              {data.hardware.vram_gb}GB VRAM ({data.hardware.gpu_name || "no GPU"})
            </span>
            <span className="px-3 py-1.5 rounded-lg bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] flex items-center gap-1.5">
              <HardDrive size={12} /> {data.hardware.free_disk_gb}GB free
            </span>
          </div>

          {data.recommended.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-[var(--color-nexus-accent)] uppercase tracking-wide">Recomendados ({data.recommended.length})</h2>
              {data.recommended.map(m => renderRow(m, "recommended"))}
            </section>
          )}

          {data.can_run.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-[var(--color-nexus-text)] uppercase tracking-wide">Todos los compatibles ({data.can_run.length})</h2>
              {data.can_run.filter(m => !data.recommended.find(r => r.name === m.name)).map(m => renderRow(m, "can_run"))}
            </section>
          )}

          {data.too_big.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-sm font-semibold text-[var(--color-nexus-muted)] uppercase tracking-wide">No caben ({data.too_big.length})</h2>
              {data.too_big.map(m => renderRow(m, "too_big"))}
            </section>
          )}

          <p className="text-[11px] text-[var(--color-nexus-muted)] italic">{data.rationale}</p>
        </>
      )}
      {!data && !loading && (
        <div className="text-center py-12 text-sm text-[var(--color-nexus-muted)]">Escaneando hardware...</div>
      )}
    </div>
  );
}
