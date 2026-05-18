import { NexusSidebar } from "@/components/sidebar/NexusSidebar";
import { HomeView } from "@/components/home/HomeView";
import { ChatView } from "@/components/chat/ChatView";
import { GemasView } from "@/components/gemas/GemasView";
import { SettingsView } from "@/components/settings/SettingsView";
import { useAppStore } from "@/stores/appStore";
import { Toaster } from "sonner";

function MainContent() {
  const view = useAppStore((s) => s.view);

  switch (view) {
    case "home":
      return <HomeView />;
    case "chat":
      return <ChatView />;
    case "gemas":
      return <GemasView />;
    case "skills":
      return <PlaceholderView title="Skills" desc="4,051 habilidades indexadas. Conectando al catálogo..." />;
    case "vision":
      return <PlaceholderView title="NexusVision" desc="Motor de visión local: Moondream2 + RapidOCR + YOLO11 + CLIP" />;
    case "brain":
      return <PlaceholderView title="Cerebro" desc="Explorador de cerebro.db y knowledge_vault" />;
    case "settings":
      return <SettingsView />;
    default:
      return <HomeView />;
  }
}

function PlaceholderView({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center animate-nexus-in">
      <h2 className="text-xl font-bold text-[var(--color-nexus-text)] mb-2">{title}</h2>
      <p className="text-sm text-[var(--color-nexus-text-sub)] max-w-md">{desc}</p>
      <div className="mt-4 px-3 py-1.5 rounded-full bg-[var(--color-nexus-surface-2)] text-xs text-[var(--color-nexus-muted)]">
        En desarrollo
      </div>
    </div>
  );
}

export function App() {
  return (
    <div className="flex h-dvh bg-[var(--color-nexus-bg)]">
      <NexusSidebar />
      <main className="flex-1 overflow-hidden">
        <MainContent />
      </main>
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
