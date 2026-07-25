import { X } from "lucide-react";

export interface EditorTab {
  id: string;
  path: string;
  name: string;
  language: string;
  modified: boolean;
}

interface Props {
  tabs: EditorTab[];
  activeTab: string | null;
  onSelect: (id: string) => void;
  onClose: (id: string) => void;
}

function detectLanguage(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    py: "python", ts: "typescript", tsx: "typescript", js: "javascript",
    jsx: "javascript", json: "json", md: "markdown", html: "html",
    css: "css", scss: "scss", yaml: "yaml", yml: "yaml", toml: "toml",
    sql: "sql", sh: "shell", bash: "shell", rs: "rust", go: "go",
    java: "java", kt: "kotlin", rb: "ruby", php: "php", xml: "xml",
    c: "c", cpp: "cpp", h: "c", hpp: "cpp", cs: "csharp",
    swift: "swift", r: "r", lua: "lua", vim: "plaintext",
    dockerfile: "dockerfile", makefile: "makefile",
  };
  return map[ext] || "plaintext";
}

export { detectLanguage };

export function EditorTabs({ tabs, activeTab, onSelect, onClose }: Props) {
  if (tabs.length === 0) return null;

  return (
    <div className="flex items-center h-9 bg-[var(--color-nexus-surface)] border-b border-[var(--color-nexus-border)] overflow-x-auto">
      {tabs.map((tab) => {
        const active = tab.id === activeTab;
        return (
          <div
            key={tab.id}
            className={`group flex items-center gap-1.5 px-3 h-full text-xs cursor-pointer border-r border-[var(--color-nexus-border)] shrink-0 transition-colors ${
              active
                ? "bg-[var(--color-nexus-bg)] text-[var(--color-nexus-text)] border-t-2 border-t-[var(--color-nexus-accent)]"
                : "bg-[var(--color-nexus-surface)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)] border-t-2 border-t-transparent"
            }`}
            onClick={() => onSelect(tab.id)}
          >
            {tab.modified && (
              <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-nexus-accent)] shrink-0" />
            )}
            <span className="truncate max-w-[120px]">{tab.name}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onClose(tab.id); }}
              className="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-[var(--color-nexus-surface-2)] transition-opacity"
            >
              <X size={11} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
