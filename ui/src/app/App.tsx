import { NexusSidebar } from "@/components/sidebar/NexusSidebar";
import { HomeView } from "@/components/home/HomeView";
import { ChatView } from "@/components/chat/ChatView";
import { GemasView } from "@/components/gemas/GemasView";
import { ManagerView } from "@/components/manager/ManagerView";
import { EditorView } from "@/components/editor/EditorView";
import { SettingsView } from "@/components/settings/SettingsView";
import { DAGView } from "@/components/panels/DAGView";
import { SessionsView } from "@/components/panels/SessionsView";
import { BrainView } from "@/components/panels/BrainView";
import { ApprovalsView } from "@/components/panels/ApprovalsView";
import { HiveView } from "@/components/panels/HiveView";
import { BudgetView } from "@/components/panels/BudgetView";
import { DoctorView } from "@/components/panels/DoctorView";
import { HallView } from "@/components/panels/HallView";
import { RecipesView } from "@/components/panels/RecipesView";
import { SkillsView } from "@/components/panels/SkillsView";
import { VaultView } from "@/components/panels/VaultView";
import { CommandsView } from "@/components/panels/CommandsView";
import { NotesView } from "@/components/panels/NotesView";
import { GuardianView } from "@/components/panels/GuardianView";
import { SchedulerView } from "@/components/panels/SchedulerView";
import { SystemView } from "@/components/panels/SystemView";
import { CreativeView } from "@/components/panels/CreativeView";
import { VoiceView } from "@/components/panels/VoiceView";
import { CookbookView } from "@/components/panels/CookbookView";
import { MonitorView } from "@/components/panels/MonitorView";
import { RightPanel } from "@/components/rightpanel/RightPanel";
import { useAppStore, type AppView } from "@/stores/appStore";
import { Toaster } from "sonner";

function MainContent() {
  const view = useAppStore((s) => s.view);

  switch (view) {
    case "home": return <HomeView />;
    case "chat": return <ChatView />;
    case "gemas": return <GemasView />;
    case "manager": return <ManagerView />;
    case "editor": return <EditorView />;
    case "skills": return <SkillsView />;
    case "settings": return <SettingsView />;
    case "dag": return <DAGView />;
    case "sessions": return <SessionsView />;
    case "brain": return <BrainView />;
    case "approvals": return <ApprovalsView />;
    case "hive": return <HiveView />;
    case "budget": return <BudgetView />;
    case "doctor": return <DoctorView />;
    case "hall": return <HallView />;
    case "recipes": return <RecipesView />;
    case "vault": return <VaultView />;
    case "commands": return <CommandsView />;
    case "notes": return <NotesView />;
    case "guardian": return <GuardianView />;
    case "scheduler": return <SchedulerView />;
    case "system": return <SystemView />;
    case "creative": return <CreativeView />;
    case "voice": return <VoiceView />;
    case "cookbook": return <CookbookView />;
    case "monitor": return <MonitorView />;
    default: return <HomeView />;
  }
}

const MASTER_TABS: Record<string, { id: AppView; label: string }[]> = {
  chat: [{ id: "chat", label: "Chat" }],
  editor: [{ id: "editor", label: "Editor" }],
  gemas: [{ id: "gemas", label: "Gemas" }],
  dag: [{ id: "dag", label: "Tareas" }],
  brain: [{ id: "brain", label: "Cerebro" }],
  skills: [{ id: "skills", label: "Skills" }],
  hive: [{ id: "hive", label: "Hive" }],
  system: [
    { id: "system", label: "Sistema" },
    { id: "doctor", label: "Doctor" },
    { id: "budget", label: "Tokens" },
    { id: "monitor", label: "Monitor" },
    { id: "cookbook", label: "Cookbook" },
  ],
};

function getMasterCategory(view: AppView): string {
  for (const [master, tabs] of Object.entries(MASTER_TABS)) {
    if (tabs.some(t => t.id === view)) return master;
  }
  return "chat";
}

function TopTabs() {
  const { view, setView } = useAppStore();
  const master = getMasterCategory(view);
  const tabs = MASTER_TABS[master];

  if (!tabs) return null;

  return (
    <div className="flex items-center px-4 h-12 border-b border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)] gap-2 overflow-x-auto shrink-0 hide-scrollbar">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setView(tab.id)}
          className={`
            px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap transition-colors
            ${view === tab.id
              ? "bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]"
              : "text-[var(--color-nexus-text-sub)] hover:bg-[var(--color-nexus-surface-2)] hover:text-[var(--color-nexus-text)]"
            }
          `}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function App() {
  return (
    <div className="flex h-dvh bg-[var(--color-nexus-bg)]">
      <NexusSidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopTabs />
        <main className="flex-1 overflow-y-auto relative">
          <MainContent />
        </main>
      </div>
      <RightPanel />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--color-nexus-surface)",
            border: "1px solid var(--color-nexus-border)",
            color: "var(--color-nexus-text)",
          },
        }}
      />
    </div>
  );
}
