import { useAppStore } from "@/stores/appStore";
import { GEMA_ICONS } from "@/components/home/HomeView";
import { Diamond } from "lucide-react";

export function GemasView() {
  const { gemas, setActiveGema, setView } = useAppStore();

  return (
    <div className="p-6 max-w-[1400px] mx-auto animate-nexus-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-[var(--color-nexus-text)]">
          22 Gemas Especializadas
        </h1>
        <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">
          Cada gema es un agente experto con modelo LLM y herramientas propias
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {gemas.map((gema) => {
          const Icon = GEMA_ICONS[gema.name] || Diamond;
          return (
            <button
              key={gema.id}
              onClick={() => {
                setActiveGema(gema.id);
                setView("chat");
              }}
              className="group bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-4 text-left hover:border-[var(--color-nexus-accent)] transition-all duration-150 active:scale-[0.98]"
            >
              {/* Icon + status */}
              <div className="flex items-start justify-between mb-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${gema.color}15` }}
                >
                  <Icon size={20} style={{ color: gema.color }} />
                </div>
                <span
                  className={`w-2 h-2 rounded-full mt-1 ${
                    gema.status === "active" ? "bg-[var(--color-nexus-online)] animate-nexus-pulse" :
                    gema.status === "error" ? "bg-[var(--color-nexus-error)]" :
                    "bg-[var(--color-nexus-idle)]"
                  }`}
                />
              </div>

              {/* Info */}
              <div className="text-sm font-semibold text-[var(--color-nexus-text)] mb-1">{gema.name}</div>
              <p className="text-xs text-[var(--color-nexus-text-sub)] line-clamp-2 mb-3">{gema.description}</p>

              {/* Meta */}
              <div className="flex items-center gap-2 text-xs text-[var(--color-nexus-muted)]">
                <span className="font-mono">{gema.model}</span>
                <span>·</span>
                <span>{gema.tools.length} tools</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
