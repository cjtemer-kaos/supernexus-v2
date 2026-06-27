import { useState } from "react";
import { useAppStore } from "@/stores/appStore";
import { AgentCard } from "@/components/manager/AgentCard";
import { GEMA_ICONS } from "@/components/home/HomeView";
import {
  Diamond, Plus, Play, Users, Zap, Send,
} from "lucide-react";

export function ManagerView() {
  const {
    gemas, agentSlots, addAgentSlot, removeAgentSlot,
    startAgentTask, stopAgentTask, retryAgentTask,
  } = useAppStore();

  const [expandedSlots, setExpandedSlots] = useState<Set<string>>(new Set());
  const [showGemaPicker, setShowGemaPicker] = useState(false);
  const [taskInputs, setTaskInputs] = useState<Record<string, string>>({});
  const [batchTask, setBatchTask] = useState("");
  const [selectedForBatch, setSelectedForBatch] = useState<Set<string>>(new Set());

  const toggleExpand = (id: string) => {
    setExpandedSlots((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const runningCount = agentSlots.filter((s) => s.status === "running").length;
  const doneCount = agentSlots.filter((s) => s.status === "done").length;

  const handleAddGema = (gemaId: string) => {
    const g = gemas.find((x) => x.id === gemaId);
    if (!g) return;
    addAgentSlot(g.id, g.name, g.color);
    setShowGemaPicker(false);
  };

  const handleStartTask = (slotId: string) => {
    const task = taskInputs[slotId]?.trim();
    if (!task) return;
    startAgentTask(slotId, task);
    setTaskInputs((p) => ({ ...p, [slotId]: "" }));
  };

  const handleBatchStart = () => {
    if (!batchTask.trim() || selectedForBatch.size === 0) return;
    for (const slotId of selectedForBatch) {
      const slot = agentSlots.find((s) => s.id === slotId);
      if (slot && (slot.status === "idle" || slot.status === "done" || slot.status === "error")) {
        startAgentTask(slotId, batchTask.trim());
      }
    }
    setBatchTask("");
    setSelectedForBatch(new Set());
  };

  const toggleBatchSelect = (id: string) => {
    setSelectedForBatch((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="flex flex-col h-full animate-nexus-in">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 h-14 border-b border-[var(--color-nexus-border)] shrink-0">
        <Users size={18} className="text-[var(--color-nexus-accent)]" />
        <div>
          <h1 className="text-sm font-bold text-[var(--color-nexus-text)]">Manager</h1>
          <p className="text-[10px] text-[var(--color-nexus-muted)] font-mono">
            {agentSlots.length} agentes · {runningCount} activos · {doneCount} completados
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={() => setShowGemaPicker(true)}
            disabled={agentSlots.length >= 8}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Plus size={13} />
            Agregar Agente
          </button>
        </div>
      </div>

      {/* Batch task bar */}
      {agentSlots.length > 1 && (
        <div className="px-6 py-2 border-b border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)]">
          <div className="flex items-center gap-2">
            <Zap size={13} className="text-[var(--color-nexus-accent)] shrink-0" />
            <span className="text-[10px] font-medium text-[var(--color-nexus-muted)] shrink-0 uppercase tracking-wider">
              Tarea en lote
            </span>
            <input
              value={batchTask}
              onChange={(e) => setBatchTask(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleBatchStart()}
              placeholder="Misma tarea para agentes seleccionados..."
              className="flex-1 bg-[var(--color-nexus-surface-2)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-1.5 text-xs text-[var(--color-nexus-text)] placeholder:text-[var(--color-nexus-muted)] outline-none focus:border-[var(--color-nexus-accent)]"
            />
            <button
              onClick={handleBatchStart}
              disabled={!batchTask.trim() || selectedForBatch.size === 0}
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent)] hover:text-white transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Play size={11} />
              Ejecutar ({selectedForBatch.size})
            </button>
          </div>
        </div>
      )}

      {/* Agent slots */}
      <div className="flex-1 overflow-y-auto p-6">
        {agentSlots.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Users size={48} className="text-[var(--color-nexus-border)] mb-4" />
            <h2 className="text-lg font-semibold text-[var(--color-nexus-text)] mb-1">
              Manager de Agentes
            </h2>
            <p className="text-sm text-[var(--color-nexus-text-sub)] max-w-md mb-4">
              Orquesta múltiples gemas trabajando en paralelo. Asigna tareas, monitorea progreso y gestiona resultados.
            </p>
            <button
              onClick={() => setShowGemaPicker(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] transition-colors"
            >
              <Plus size={16} />
              Agregar primer agente
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {agentSlots.map((slot) => (
              <div key={slot.id}>
                {/* Batch checkbox */}
                {agentSlots.length > 1 && (
                  <div className="flex items-center gap-2 mb-1.5 pl-1">
                    <button
                      onClick={() => toggleBatchSelect(slot.id)}
                      className={`w-3.5 h-3.5 rounded border transition-colors ${
                        selectedForBatch.has(slot.id)
                          ? "bg-[var(--color-nexus-accent)] border-[var(--color-nexus-accent)]"
                          : "border-[var(--color-nexus-border)] hover:border-[var(--color-nexus-accent)]"
                      }`}
                    />
                    <span className="text-[10px] text-[var(--color-nexus-muted)]">Seleccionar</span>
                  </div>
                )}

                <AgentCard
                  slot={slot}
                  onStop={() => stopAgentTask(slot.id)}
                  onRemove={() => removeAgentSlot(slot.id)}
                  onRetry={() => retryAgentTask(slot.id)}
                  expanded={expandedSlots.has(slot.id)}
                  onToggleExpand={() => toggleExpand(slot.id)}
                />

                {/* Task input for idle/done slots */}
                {(slot.status === "idle" || slot.status === "done" || slot.status === "error") && (
                  <div className="flex items-center gap-2 mt-2">
                    <input
                      value={taskInputs[slot.id] || ""}
                      onChange={(e) => setTaskInputs((p) => ({ ...p, [slot.id]: e.target.value }))}
                      onKeyDown={(e) => e.key === "Enter" && handleStartTask(slot.id)}
                      placeholder={`Tarea para ${slot.gemaName}...`}
                      className="flex-1 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-lg px-3 py-2 text-xs text-[var(--color-nexus-text)] placeholder:text-[var(--color-nexus-muted)] outline-none focus:border-[var(--color-nexus-accent)]"
                    />
                    <button
                      onClick={() => handleStartTask(slot.id)}
                      disabled={!taskInputs[slot.id]?.trim()}
                      className="p-2 rounded-lg bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                    >
                      <Send size={13} />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Gema picker modal */}
      {showGemaPicker && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setShowGemaPicker(false)}
        >
          <div
            className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-5 w-full max-w-2xl max-h-[70vh] overflow-y-auto animate-nexus-in"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-sm font-semibold text-[var(--color-nexus-text)] mb-4">
              Seleccionar Gema para el Manager
            </h3>
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {gemas.map((g) => {
                const GIcon = GEMA_ICONS[g.name] || Diamond;
                const alreadyAdded = agentSlots.some((s) => s.gemaId === g.id);
                return (
                  <button
                    key={g.id}
                    onClick={() => handleAddGema(g.id)}
                    disabled={alreadyAdded}
                    className={`flex items-center gap-2 p-3 rounded-lg border text-left transition-all ${
                      alreadyAdded
                        ? "border-[var(--color-nexus-border)] opacity-40 cursor-not-allowed"
                        : "border-[var(--color-nexus-border)] hover:border-[var(--color-nexus-accent)] active:scale-[0.97]"
                    }`}
                  >
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                      style={{ backgroundColor: `${g.color}15` }}
                    >
                      <GIcon size={14} style={{ color: g.color }} />
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-[var(--color-nexus-text)] truncate">{g.name}</div>
                      <div className="text-[10px] text-[var(--color-nexus-muted)] font-mono truncate">{g.model}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
