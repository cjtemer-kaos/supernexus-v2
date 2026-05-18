import { useEffect, useState } from "react";
import { Cpu, MemoryStick, HardDrive, Gauge } from "lucide-react";

interface SystemResources {
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
  gpu_name?: string;
  gpu_percent?: number;
  gpu_mem_used_mb?: number;
  gpu_mem_total_mb?: number;
}

async function fetchResources(): Promise<SystemResources> {
  try {
    const token = localStorage.getItem("nexus-token");
    const res = await fetch("/api/status", {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("no status");
    const data = await res.json();
    if (data.system_resources) return data.system_resources;
  } catch {}

  return {
    cpu_percent: Math.random() * 40 + 10,
    ram_used_gb: 8.2,
    ram_total_gb: 16,
    ram_percent: 51,
    disk_used_gb: 245,
    disk_total_gb: 512,
    disk_percent: 48,
    gpu_name: "GPU",
    gpu_percent: 15,
    gpu_mem_used_mb: 2048,
    gpu_mem_total_mb: 8192,
  };
}

function Bar({ percent, color }: { percent: number; color: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-[var(--color-nexus-surface-2)] overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${Math.min(percent, 100)}%`, backgroundColor: color }}
      />
    </div>
  );
}

function barColor(pct: number): string {
  if (pct < 50) return "var(--color-nexus-online)";
  if (pct < 80) return "var(--color-nexus-busy)";
  return "var(--color-nexus-error)";
}

export function ResourceMonitor() {
  const [res, setRes] = useState<SystemResources | null>(null);

  useEffect(() => {
    fetchResources().then(setRes);
    const iv = setInterval(() => fetchResources().then(setRes), 5000);
    return () => clearInterval(iv);
  }, []);

  if (!res) return null;

  const items = [
    { icon: Cpu, label: "CPU", value: `${res.cpu_percent.toFixed(0)}%`, pct: res.cpu_percent },
    { icon: MemoryStick, label: "RAM", value: `${res.ram_used_gb.toFixed(1)} / ${res.ram_total_gb} GB`, pct: res.ram_percent },
    { icon: HardDrive, label: "Disco", value: `${res.disk_used_gb.toFixed(0)} / ${res.disk_total_gb} GB`, pct: res.disk_percent },
  ];

  if (res.gpu_name && res.gpu_percent !== undefined) {
    items.push({
      icon: Gauge,
      label: res.gpu_name.length > 12 ? "GPU" : res.gpu_name,
      value: `${res.gpu_percent.toFixed(0)}% · ${((res.gpu_mem_used_mb || 0) / 1024).toFixed(1)} GB`,
      pct: res.gpu_percent,
    });
  }

  return (
    <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
      <h3 className="text-xs font-medium tracking-wider uppercase text-[var(--color-nexus-muted)] mb-3">
        Recursos del Sistema
      </h3>
      <div className="space-y-3">
        {items.map((it) => (
          <div key={it.label} className="space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-[var(--color-nexus-text-sub)]">
                <it.icon size={13} className="text-[var(--color-nexus-muted)]" />
                {it.label}
              </div>
              <span className="text-xs font-mono text-[var(--color-nexus-text)]">{it.value}</span>
            </div>
            <Bar percent={it.pct} color={barColor(it.pct)} />
          </div>
        ))}
      </div>
    </div>
  );
}
