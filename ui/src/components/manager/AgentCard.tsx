import { useRef, useEffect } from "react";
import { Square, RotateCcw, X, ChevronDown, ChevronUp } from "lucide-react";
import { GEMA_ICONS } from "@/components/home/HomeView";
import { Diamond } from "lucide-react";
import type { AgentSlot } from "@/stores/appStore";

interface Props {
  slot: AgentSlot;
  onStop: () => void;
  onRemove: () => void;
  onRetry: () => void;
  expanded: boolean;
  onToggleExpand: () => void;
}

const STATUS_COLORS: Record<AgentSlot["status"], string> = {
  idle: "var(--color-nexus-muted)",
  running: "var(--color-nexus-accent)",
  done: "var(--color-nexus-online)",
  error: "var(--color-nexus-error)",
};

const STATUS_LABELS: Record<AgentSlot["status"], string> = {
  idle: "Esperando",
  running: "Ejecutando",
  done: "Completado",
  error: "Error",
};

export function AgentCard({ slot, onStop, onRemove, onRetry, expanded, onToggleExpand }: Props) {
  const logRef = useRef<HTMLDivElement>(null);
  const Icon = GEMA_ICONS[slot.gemaName] || Diamond;

  useEffect(() => {
    if (expanded && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [slot.logs.length, expanded]);

  const elapsed = slot.startedAt
    ? Math.floor((Date.now() - slot.startedAt) / 1000)
    : 0;
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;

  return (
    <div
      className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl overflow-hidden transition-all"
      style={{
        borderColor: slot.status === "running"
          ? "color-mix(in srgb, var(--color-nexus-accent) 40%, transparent)"
          : undefined,
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${slot.gemaColor}15` }}
        >
          <Icon size={16} style={{ color: slot.gemaColor }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-[var(--color-nexus-text)] truncate">
              {slot.gemaName}
            </span>
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{
                backgroundColor: STATUS_COLORS[slot.status],
                animation: slot.status === "running" ? "pulse 2s infinite" : undefined,
              }}
            />
            <span className="text-[10px] font-mono text-[var(--color-nexus-muted)]">
              {STATUS_LABELS[slot.status]}
            </span>
          </div>
          {slot.task && (
            <p className="text-xs text-[var(--color-nexus-text-sub)] truncate mt-0.5">
              {slot.task}
            </p>
          )}
        </div>

        {/* Timer */}
        {slot.status === "running" && (
          <span className="text-[10px] font-mono text-[var(--color-nexus-muted)] shrink-0">
            {mins}:{secs.toString().padStart(2, "0")}
          </span>
        )}

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {slot.status === "running" && (
            <button
              onClick={onStop}
              className="p-1.5 rounded-md hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-error)] transition-colors"
              title="Detener"
            >
              <Square size={13} />
            </button>
          )}
          {(slot.status === "done" || slot.status === "error") && (
            <button
              onClick={onRetry}
              className="p-1.5 rounded-md hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)] transition-colors"
              title="Reintentar"
            >
              <RotateCcw size={13} />
            </button>
          )}
          <button
            onClick={onToggleExpand}
            className="p-1.5 rounded-md hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] transition-colors"
            title={expanded ? "Colapsar" : "Expandir"}
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
          <button
            onClick={onRemove}
            className="p-1.5 rounded-md hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-error)] transition-colors"
            title="Remover"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {slot.status === "running" && (
        <div className="h-0.5 bg-[var(--color-nexus-surface-2)]">
          <div
            className="h-full bg-[var(--color-nexus-accent)] transition-all duration-500"
            style={{
              width: slot.progress != null ? `${slot.progress}%` : undefined,
              animation: slot.progress == null ? "indeterminate 1.5s infinite linear" : undefined,
            }}
          />
        </div>
      )}

      {/* Logs */}
      {expanded && (
        <div
          ref={logRef}
          className="max-h-48 overflow-y-auto px-4 py-2 bg-[var(--color-nexus-bg)] border-t border-[var(--color-nexus-border)] font-mono text-[11px] leading-relaxed space-y-0.5"
        >
          {slot.logs.length === 0 ? (
            <div className="text-[var(--color-nexus-muted)] italic">Sin actividad aún...</div>
          ) : (
            slot.logs.map((log, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-[var(--color-nexus-muted)] shrink-0 select-none">
                  {log.time}
                </span>
                <span
                  style={{
                    color:
                      log.type === "error" ? "var(--color-nexus-error)" :
                      log.type === "success" ? "var(--color-nexus-online)" :
                      log.type === "info" ? "var(--color-nexus-accent)" :
                      "var(--color-nexus-text-sub)",
                  }}
                >
                  {log.text}
                </span>
              </div>
            ))
          )}

          {/* Streaming output */}
          {slot.output && (
            <div className="mt-2 pt-2 border-t border-[var(--color-nexus-border)]">
              <div className="text-[var(--color-nexus-text)] whitespace-pre-wrap">{slot.output}</div>
              {slot.status === "running" && (
                <span className="inline-block w-1.5 h-3 bg-[var(--color-nexus-accent)] animate-pulse ml-0.5" />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
