import {
  Home, MessageSquare, Diamond, Sparkles,
  Settings, PanelLeftClose, PanelLeft,
  GitBranch, Brain, Network, Activity, Code2
} from "lucide-react";
import { useAppStore, type AppView } from "@/stores/appStore";

interface NavItem { id: AppView; label: string; icon: typeof Home; }

const MASTER_ITEMS: NavItem[] = [
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "editor", label: "Editor", icon: Code2 },
  { id: "gemas", label: "Gemas", icon: Diamond },
  { id: "dag", label: "Tareas", icon: GitBranch },
  { id: "brain", label: "Cerebro", icon: Brain },
  { id: "skills", label: "Skills", icon: Sparkles },
  { id: "hive", label: "Hive", icon: Network },
  { id: "system", label: "Sistema", icon: Activity },
];

export function NexusSidebar() {
  const { view, setView, sidebarCollapsed, toggleSidebar } = useAppStore();

  return (
    <aside
      className="flex flex-col h-full border-r border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)] transition-all duration-200"
      style={{ width: sidebarCollapsed ? 48 : 220 }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 h-12 border-b border-[var(--color-nexus-border)]">
        {!sidebarCollapsed && (
          <span className="font-bold text-sm tracking-tight text-[var(--color-nexus-accent)]">
            SuperNEXUS
          </span>
        )}
        <button
          onClick={toggleSidebar}
          className="ml-auto p-1.5 rounded-md hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] transition-colors"
        >
          {sidebarCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-2 px-1.5 space-y-1 overflow-y-auto">
        <div className="space-y-1">

          {MASTER_ITEMS.map((item) => {
            const active = view === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setView(item.id)}
                className={`
                  w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
                  transition-colors duration-150 min-h-[32px]
                  ${active

                      ? "bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]"
                      : "text-[var(--color-nexus-text-sub)] hover:bg-[var(--color-nexus-surface-2)] hover:text-[var(--color-nexus-text)]"
                    }
                  `}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  <item.icon size={16} className="shrink-0" />
                  {!sidebarCollapsed && <span>{item.label}</span>}
                </button>
              );
            })}
        </div>
      </nav>

      {/* Footer — settings & branding */}
      <div className="px-1.5 pb-3 border-t border-[var(--color-nexus-border)] pt-2 space-y-2">
        <button
          onClick={() => setView("settings")}
          className={`
            w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium
            transition-colors duration-150 min-h-[32px]
            ${view === "settings"
              ? "bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]"
              : "text-[var(--color-nexus-text-sub)] hover:bg-[var(--color-nexus-surface-2)] hover:text-[var(--color-nexus-text)]"
            }
          `}
        >
          <Settings size={16} className="shrink-0" />
          {!sidebarCollapsed && <span>Config</span>}
        </button>
        
        {!sidebarCollapsed && (
          <div className="pt-2 border-t border-[var(--color-nexus-border-light)]/30 flex justify-center items-center gap-1.5">
            <img src="/ui/kaos.png" alt="KAOS_MCS" className="h-5 w-5 rounded-sm opacity-70" />
            <span className="text-[10px] font-mono font-bold tracking-widest text-[var(--color-nexus-muted)]/60 select-none">
              KAOS_MCS
            </span>
          </div>
        )}
      </div>
    </aside>
  );
}
