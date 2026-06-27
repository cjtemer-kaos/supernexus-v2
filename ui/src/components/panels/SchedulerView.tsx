import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Clock, RefreshCw, Plus, RotateCcw, Eye } from "lucide-react";



export function SchedulerView() {
  const [scheduler, setScheduler] = useState<any>(null);
  const [retry, setRetry] = useState<any>(null);
  const [review, setReview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [taskName, setTaskName] = useState("");
  const [taskCron, setTaskCron] = useState("");
  const [taskAction, setTaskAction] = useState("");
  const [result, setResult] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [s, rt, rv] = await Promise.all([
        authFetch(`${API}/api/scheduler/status`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/retry/status`).then(r => r.json()).catch(() => null),
        authFetch(`${API}/api/review/status`).then(r => r.json()).catch(() => null),
      ]);
      setScheduler(s); setRetry(rt); setReview(rv);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const addTask = async () => {
    if (!taskName.trim()) return;
    const res = await authFetch(`${API}/api/scheduler/add`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: taskName, cron: taskCron, action: taskAction }),
    });
    setResult(JSON.stringify(await res.json(), null, 2));
    setTaskName(""); setTaskCron(""); setTaskAction("");
    refresh();
  };

  const triggerReview = async () => {
    const res = await authFetch(`${API}/api/review/trigger`, { method: "POST" });
    setResult(JSON.stringify(await res.json(), null, 2));
  };

  const InfoBlock = ({ title, data, icon }: { title: string; data: any; icon: React.ReactNode }) => (
    <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <span className="text-sm font-semibold text-[var(--color-nexus-text)]">{title}</span>
      </div>
      {data ? (
        <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-32 overflow-auto">{JSON.stringify(data, null, 2)}</pre>
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
            <Clock size={22} className="text-[var(--color-nexus-accent)]" /> Scheduler & Automation
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">Tareas programadas, reintentos y revisiones</p>
        </div>
        <button onClick={refresh} className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]">
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <InfoBlock title="Scheduler" data={scheduler} icon={<Clock size={14} className="text-[var(--color-nexus-accent)]" />} />
        <InfoBlock title="Retry Manager" data={retry} icon={<RotateCcw size={14} className="text-yellow-500" />} />
        <InfoBlock title="Review Triggers" data={review} icon={<Eye size={14} className="text-[var(--color-nexus-online)]" />} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider flex items-center gap-1.5"><Plus size={11} /> Agregar tarea programada</div>
          <input value={taskName} onChange={e => setTaskName(e.target.value)} placeholder="Nombre de la tarea"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none" />
          <input value={taskCron} onChange={e => setTaskCron(e.target.value)} placeholder="Expresión cron (ej: */5 * * * *)"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs font-mono text-[var(--color-nexus-text)] outline-none" />
          <input value={taskAction} onChange={e => setTaskAction(e.target.value)} placeholder="Acción / comando"
            className="w-full bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] outline-none" />
          <button onClick={addTask} className="px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white">Agregar</button>
        </div>

        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 space-y-3">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider">Acciones rápidas</div>
          <button onClick={triggerReview} className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)] hover:text-white transition-colors">
            <Eye size={12} /> Trigger Review Manual
          </button>
        </div>
      </div>

      {result && (
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4">
          <div className="text-xs font-medium text-[var(--color-nexus-muted)] uppercase tracking-wider mb-2">Resultado</div>
          <pre className="text-[11px] font-mono text-[var(--color-nexus-text-sub)] max-h-48 overflow-auto">{result}</pre>
        </div>
      )}
    </div>
  );
}
