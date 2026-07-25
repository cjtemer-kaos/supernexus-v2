import { useState, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import Editor from "@monaco-editor/react";
import { FileExplorer } from "@/components/editor/FileExplorer";
import { EditorTabs, detectLanguage, type EditorTab } from "@/components/editor/EditorTabs";
import { TerminalPanel } from "@/components/editor/TerminalPanel";
import { Save, Code2, PanelLeftClose, PanelLeft } from "lucide-react";
import { toast } from "sonner";


const DEFAULT_ROOT = "D:\\ias\\proyectos\\supernexus-v2";

async function readFile(path: string): Promise<string> {
  const res = await authFetch(`${API}/api/fs/read`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) throw new Error("Failed to read file");
  const data = await res.json();
  return data.content || "";
}

async function writeFile(path: string, content: string): Promise<void> {
  const res = await authFetch(`${API}/api/fs/write`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  if (!res.ok) throw new Error("Failed to write file");
}

export function EditorView() {
  const [rootPath, setRootPath] = useState(DEFAULT_ROOT);
  const [tabs, setTabs] = useState<EditorTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [contents, setContents] = useState<Record<string, string>>({});
  const [originals, setOriginals] = useState<Record<string, string>>({});
  const [showExplorer, setShowExplorer] = useState(true);
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const activeTab = tabs.find((t) => t.id === activeTabId) || null;

  const openFile = useCallback(async (path: string) => {
    // Already open?
    const existing = tabs.find((t) => t.path === path);
    if (existing) {
      setActiveTabId(existing.id);
      return;
    }

    try {
      const content = await readFile(path);
      const name = path.split(/[\\/]/).pop() || "file";
      const lang = detectLanguage(name);
      const id = crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36);
      const tab: EditorTab = { id, path, name, language: lang, modified: false };

      setTabs((prev) => [...prev, tab]);
      setContents((prev) => ({ ...prev, [id]: content }));
      setOriginals((prev) => ({ ...prev, [id]: content }));
      setActiveTabId(id);
    } catch {
      toast.error("No se pudo abrir el archivo");
    }
  }, [tabs]);

  const closeTab = useCallback((id: string) => {
    setTabs((prev) => {
      const next = prev.filter((t) => t.id !== id);
      if (activeTabId === id) {
        const idx = prev.findIndex((t) => t.id === id);
        const newActive = next[Math.min(idx, next.length - 1)]?.id || null;
        setActiveTabId(newActive);
      }
      return next;
    });
    setContents((prev) => { const n = { ...prev }; delete n[id]; return n; });
    setOriginals((prev) => { const n = { ...prev }; delete n[id]; return n; });
  }, [activeTabId]);

  const handleContentChange = useCallback((value: string | undefined) => {
    if (!activeTabId || value === undefined) return;
    setContents((prev) => ({ ...prev, [activeTabId]: value }));
    setTabs((prev) =>
      prev.map((t) =>
        t.id === activeTabId ? { ...t, modified: value !== originals[activeTabId] } : t
      )
    );
  }, [activeTabId, originals]);

  const saveFile = useCallback(async () => {
    if (!activeTab) return;
    setSaving(true);
    try {
      await writeFile(activeTab.path, contents[activeTab.id] || "");
      setOriginals((prev) => ({ ...prev, [activeTab.id]: contents[activeTab.id] }));
      setTabs((prev) => prev.map((t) => t.id === activeTab.id ? { ...t, modified: false } : t));
      toast.success(`Guardado: ${activeTab.name}`);
    } catch {
      toast.error("Error al guardar");
    } finally {
      setSaving(false);
    }
  }, [activeTab, contents]);

  // Ctrl+S handler
  const handleEditorMount = useCallback((_editor: any, monaco: any) => {
    monaco.editor.defineTheme("nexus-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "3a8a9a", fontStyle: "italic" },
        { token: "keyword", foreground: "00d4ff" },
        { token: "string", foreground: "00ff88" },
        { token: "number", foreground: "ff6b00" },
        { token: "type", foreground: "ffcc00" },
        { token: "function", foreground: "8ffcff" },
        { token: "variable", foreground: "d8f8ff" },
        { token: "constant", foreground: "ff6b00" },
        { token: "delimiter", foreground: "5ab8cc" },
      ],
      colors: {
        "editor.background": "#00060a",
        "editor.foreground": "#8ffcff",
        "editor.lineHighlightBackground": "#010f18",
        "editor.selectionBackground": "#0d3347",
        "editor.inactiveSelectionBackground": "#0d334755",
        "editorCursor.foreground": "#00d4ff",
        "editorWhitespace.foreground": "#0d3347",
        "editorIndentGuide.background": "#0d3347",
        "editorIndentGuide.activeBackground": "#1a5c7a",
        "editorLineNumber.foreground": "#3a8a9a",
        "editorLineNumber.activeForeground": "#00d4ff",
        "editorBracketMatch.background": "#0d3347",
        "editorBracketMatch.border": "#00d4ff",
        "editorWidget.background": "#010d14",
        "editorWidget.border": "#0d3347",
        "input.background": "#010d14",
        "input.border": "#0d3347",
        "input.foreground": "#8ffcff",
        "list.activeSelectionBackground": "#0d3347",
        "list.activeSelectionForeground": "#00d4ff",
        "list.hoverBackground": "#010f18",
        "list.inactiveSelectionBackground": "#0d334755",
        "scrollbar.shadow": "#00000000",
        "scrollbarSlider.background": "#0d334755",
        "scrollbarSlider.hoverBackground": "#0d3347",
        "scrollbarSlider.activeBackground": "#1a5c7a",
        "minimap.background": "#00060a",
      },
    });
    monaco.editor.setTheme("nexus-dark");
    _editor.addAction({
      id: "save-file",
      label: "Save File",
      keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS],
      run: () => saveFile(),
    });
  }, [saveFile]);

  return (
    <div className="flex flex-col h-full animate-nexus-in">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 h-10 border-b border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)] shrink-0">
        <button
          onClick={() => setShowExplorer(!showExplorer)}
          className="p-1 rounded hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] transition-colors"
        >
          {showExplorer ? <PanelLeftClose size={14} /> : <PanelLeft size={14} />}
        </button>
        <Code2 size={14} className="text-[var(--color-nexus-accent)]" />
        <span className="text-xs font-semibold text-[var(--color-nexus-text)]">Editor</span>

        <div className="ml-auto flex items-center gap-2">
          {activeTab?.modified && (
            <button
              onClick={saveFile}
              disabled={saving}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-50 transition-colors"
            >
              <Save size={11} />
              {saving ? "Guardando..." : "Guardar"}
            </button>
          )}
          <span className="text-[10px] font-mono text-[var(--color-nexus-muted)]">
            {activeTab?.language || ""}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* File Explorer */}
        {showExplorer && (
          <div
            className="border-r border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)] overflow-hidden shrink-0"
            style={{ width: 240 }}
          >
            <FileExplorer
              rootPath={rootPath}
              onFileSelect={openFile}
              onRootChange={setRootPath}
              selectedFile={activeTab?.path || null}
            />
          </div>
        )}

        {/* Editor area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <EditorTabs
            tabs={tabs}
            activeTab={activeTabId}
            onSelect={setActiveTabId}
            onClose={closeTab}
          />

          {/* Monaco Editor */}
          <div className="flex-1 overflow-hidden">
            {activeTab ? (
              <Editor
                language={activeTab.language}
                value={contents[activeTab.id] || ""}
                onChange={handleContentChange}
                onMount={handleEditorMount}
                theme="nexus-dark"
                options={{
                  fontSize: 13,
                  fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace",
                  fontLigatures: true,
                  minimap: { enabled: true, scale: 1 },
                  scrollBeyondLastLine: false,
                  wordWrap: "on",
                  tabSize: 2,
                  renderWhitespace: "selection",
                  bracketPairColorization: { enabled: true },
                  smoothScrolling: true,
                  cursorBlinking: "smooth",
                  cursorSmoothCaretAnimation: "on",
                  padding: { top: 8 },
                }}
              />
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center bg-[var(--color-nexus-bg)]">
                <Code2 size={48} className="text-[var(--color-nexus-border)] mb-4" />
                <h2 className="text-lg font-semibold text-[var(--color-nexus-text)] mb-1">
                  Editor de Código
                </h2>
                <p className="text-sm text-[var(--color-nexus-text-sub)] max-w-md">
                  Selecciona un archivo del explorador para comenzar a editar.
                </p>
                <div className="flex gap-3 mt-4 text-[10px] text-[var(--color-nexus-muted)]">
                  <kbd className="px-2 py-1 rounded bg-[var(--color-nexus-surface-2)] font-mono">Ctrl+S</kbd>
                  <span>Guardar</span>
                </div>
              </div>
            )}
          </div>

          {/* Terminal */}
          <TerminalPanel
            cwd={rootPath}
            expanded={terminalOpen}
            onToggle={() => setTerminalOpen(!terminalOpen)}
          />
        </div>
      </div>
    </div>
  );
}
