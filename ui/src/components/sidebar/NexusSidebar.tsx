import {
  Home, MessageSquare, Diamond, Sparkles,
  Eye, Brain, Settings, PanelLeftClose, PanelLeft,
} from "lucide-react";
import { useAppStore, type AppView } from "@/stores/appStore";

const NAV_ITEMS: { id: AppView; label: string; icon: typeof Home }[] = [
  { id: "home", label: "Inicio", icon: Home },
  { id: "chat", label: "Chat", icon: MessageSquare },
  { id: "gemas", label: "Gemas", icon: Diamond },
  { id: "skills", label: "Skills", icon: Sparkles },
  { id: "vision", label: "Vision", icon: Eye },
  { id: "brain", label: "Cerebro", icon: Brain },
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
      <nav className="flex-1 py-2 px-1.5 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const active = view === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`
                w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium
                transition-colors duration-150 min-h-[40px]
                ${active
                  ? "bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]"
                  : "text-[var(--color-nexus-text-sub)] hover:bg-[var(--color-nexus-surface-2)] hover:text-[var(--color-nexus-text)]"
                }
              `}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <item.icon size={18} className="shrink-0" />
              {!sidebarCollapsed && <span>{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {/* Footer — settings */}
      <div className="px-1.5 pb-2 border-t border-[var(--color-nexus-border)] pt-2">
        <button
          onClick={() => setView("settings")}
          className={`
            w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium
            transition-colors duration-150 min-h-[40px]
            ${view === "settings"
              ? "bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]"
              : "text-[var(--color-nexus-text-sub)] hover:bg-[var(--color-nexus-surface-2)] hover:text-[var(--color-nexus-text)]"
            }
          `}
        >
          <Settings size={18} className="shrink-0" />
          {!sidebarCollapsed && <span>Config</span>}
        </button>
      </div>
    </aside>
  );
}
