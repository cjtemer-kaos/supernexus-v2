import { useAppStore } from "@/stores/appStore";
import { ResourceMonitor } from "@/components/home/ResourceMonitor";
import {
  Target, Code2, BookOpen, Building2, Palette, Brain, BarChart3,
  Wrench, Search, Zap, FlaskConical, Shield, Rocket, GraduationCap,
  Library, Eye, Terminal, Box, Figma, Music, PenTool, Clapperboard,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const GEMA_ICONS: Record<string, LucideIcon> = {
  Director: Target, Code: Code2, Scholar: BookOpen, Architect: Building2,
  Creative: Palette, Sage: Brain, Analyst: BarChart3, Engineer: Wrench,
  Debugger: Search, Optimizer: Zap, Tester: FlaskConical, Security: Shield,
  DevOps: Rocket, Trainer: GraduationCap, Biblioteca: Library, Vision: Eye,
  OpenCode: Terminal, Codex: Box, Design: Figma, Music: Music,
  Prompter: PenTool, Producer: Clapperboard,
};

export function HomeView() {
  const { gemas, setView } = useAppStore();
  const activeGemas = gemas.filter((g) => g.status === "active");

  return (
    <div className="p-6 space-y-6 max-w-[1400px] mx-auto animate-nexus-in">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tighter text-[var(--color-nexus-text)]">
            SuperNEXUS <span className="text-[var(--color-nexus-accent)]">v2</span>
          </h1>
          <p className="text-sm text-[var(--color-nexus-text-sub)] mt-1">
            {activeGemas.length} gemas en ejecucion · {gemas.length} disponibles
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs text-[var(--color-nexus-muted)] font-mono">
            {new Date().toLocaleDateString("es", { weekday: "long", day: "numeric", month: "long" })}
          </div>
        </div>
      </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-4 gap-4">
        {/* Gemas Activas — 2x2 */}
        <button
          onClick={() => setView("gemas")}
          className="col-span-2 row-span-2 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-5 text-left hover:border-[var(--color-nexus-accent)] transition-colors"
        >
          <h3 className="text-xs font-medium tracking-wider uppercase text-[var(--color-nexus-muted)] mb-4">
            Gemas Activas
          </h3>
          <div className="flex flex-wrap gap-2">
            {activeGemas.map((g) => {
              const Icon = GEMA_ICONS[g.name] || Diamond;
              return (
                <div
                  key={g.id}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium"
                  style={{ backgroundColor: `${g.color}15`, color: g.color }}
                >
                  <Icon size={14} />
                  {g.name}
                </div>
              );
            })}
          </div>
        </button>

        {/* Stats */}
        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-5">
          <h3 className="text-xs font-medium tracking-wider uppercase text-[var(--color-nexus-muted)] mb-2">
            Gemas
          </h3>
          <div className="text-2xl font-bold tracking-tight text-[var(--color-nexus-text)]">
            {gemas.length}
          </div>
          <div className="text-xs text-[var(--color-nexus-text-sub)] mt-0.5">
            {activeGemas.length} activas
          </div>
        </div>

        <div className="bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-5">
          <h3 className="text-xs font-medium tracking-wider uppercase text-[var(--color-nexus-muted)] mb-2">
            Skills
          </h3>
          <div className="text-2xl font-bold tracking-tight text-[var(--color-nexus-text)]">
            4,051
          </div>
          <div className="text-xs text-[var(--color-nexus-text-sub)] mt-0.5">
            indexados
          </div>
        </div>

        {/* Chat card */}
        <button
          onClick={() => setView("chat")}
          className="col-span-2 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl p-5 text-left hover:border-[var(--color-nexus-accent)] transition-colors"
        >
          <h3 className="text-xs font-medium tracking-wider uppercase text-[var(--color-nexus-muted)] mb-2">
            Chat con el Director
          </h3>
          <p className="text-sm text-[var(--color-nexus-text-sub)]">
            Habla con el Director o selecciona una gema para interactuar directamente.
          </p>
        </button>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => setView("chat")}
          className="px-4 py-2.5 bg-[var(--color-nexus-accent)] text-white rounded-lg text-sm font-medium hover:bg-[var(--color-nexus-accent-dim)] transition-colors active:scale-[0.98]"
        >
          Nuevo Chat
        </button>
        <button
          onClick={() => setView("gemas")}
          className="px-4 py-2.5 bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-text)] rounded-lg text-sm font-medium hover:bg-[var(--color-nexus-border)] transition-colors"
        >
          Ver 22 Gemas
        </button>
      </div>

      {/* Resource Monitor */}
      <ResourceMonitor />
    </div>
  );
}

// Re-export for use in other components
import { Diamond } from "lucide-react";
export { GEMA_ICONS };
