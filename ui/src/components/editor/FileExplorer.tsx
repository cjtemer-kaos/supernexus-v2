import { useState, useEffect, useCallback } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import {
  ChevronRight, ChevronDown, File, Folder, FolderOpen,
  RefreshCw, FolderUp,
} from "lucide-react";

export interface FileEntry {
  name: string;
  path: string;
  isDir: boolean;
  size?: number;
  children?: FileEntry[];
}

interface Props {
  rootPath: string;
  onFileSelect: (path: string) => void;
  onRootChange: (path: string) => void;
  selectedFile: string | null;
}



const EXT_ICONS: Record<string, string> = {
  py: "🐍", ts: "📘", tsx: "⚛️", js: "📒", json: "📋",
  md: "📝", yaml: "⚙️", yml: "⚙️", toml: "⚙️",
  html: "🌐", css: "🎨", sql: "🗄️", sh: "🖥️",
};

function getFileIcon(name: string): string {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  return EXT_ICONS[ext] || "";
}

function getLanguageColor(name: string): string | undefined {
  const ext = name.split(".").pop()?.toLowerCase() || "";
  const colors: Record<string, string> = {
    py: "#3572A5", ts: "#3178c6", tsx: "#3178c6", js: "#f1e05a",
    json: "#292929", md: "#083fa1", html: "#e34c26", css: "#563d7c",
    yaml: "#cb171e", yml: "#cb171e", sql: "#e38c00", sh: "#89e051",
    rs: "#dea584", go: "#00ADD8", java: "#b07219",
  };
  return colors[ext];
}

async function listDir(dirPath: string): Promise<FileEntry[]> {
  try {
    const res = await authFetch(`${API}/api/fs/list`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: dirPath }),
    });
    if (!res.ok) throw new Error("Failed");
    const data = await res.json();
    return data.entries || [];
  } catch {
    return [];
  }
}

function TreeNode({
  entry,
  depth,
  onFileSelect,
  selectedFile,
}: {
  entry: FileEntry;
  depth: number;
  onFileSelect: (path: string) => void;
  selectedFile: string | null;
}) {
  const [expanded, setExpanded] = useState(false);
  const [children, setChildren] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const toggle = async () => {
    if (!entry.isDir) {
      onFileSelect(entry.path);
      return;
    }
    if (!expanded) {
      setLoading(true);
      const items = await listDir(entry.path);
      setChildren(items);
      setLoading(false);
    }
    setExpanded(!expanded);
  };

  const isSelected = selectedFile === entry.path;
  const langColor = !entry.isDir ? getLanguageColor(entry.name) : undefined;

  return (
    <div>
      <button
        onClick={toggle}
        className={`w-full flex items-center gap-1 px-2 py-[3px] text-left text-xs hover:bg-[var(--color-nexus-surface-2)] transition-colors rounded-sm ${
          isSelected ? "bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-accent)]" : "text-[var(--color-nexus-text-sub)]"
        }`}
        style={{ paddingLeft: `${depth * 14 + 6}px` }}
      >
        {entry.isDir ? (
          <>
            {loading ? (
              <RefreshCw size={12} className="animate-spin shrink-0 text-[var(--color-nexus-muted)]" />
            ) : expanded ? (
              <ChevronDown size={12} className="shrink-0 text-[var(--color-nexus-muted)]" />
            ) : (
              <ChevronRight size={12} className="shrink-0 text-[var(--color-nexus-muted)]" />
            )}
            {expanded ? (
              <FolderOpen size={13} className="shrink-0 text-[var(--color-nexus-accent)]" />
            ) : (
              <Folder size={13} className="shrink-0 text-[var(--color-nexus-muted)]" />
            )}
          </>
        ) : (
          <>
            <span className="w-3 shrink-0" />
            {langColor ? (
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: langColor }} />
            ) : (
              <File size={13} className="shrink-0 text-[var(--color-nexus-muted)]" />
            )}
          </>
        )}
        <span className="truncate ml-1">
          {getFileIcon(entry.name)} {entry.name}
        </span>
      </button>
      {expanded && children.length > 0 && (
        <div>
          {children.map((child) => (
            <TreeNode
              key={child.path}
              entry={child}
              depth={depth + 1}
              onFileSelect={onFileSelect}
              selectedFile={selectedFile}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileExplorer({ rootPath, onFileSelect, onRootChange, selectedFile }: Props) {
  const [entries, setEntries] = useState<FileEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    const items = await listDir(rootPath);
    setEntries(items);
    setLoading(false);
  }, [rootPath]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const goUp = () => {
    const parent = rootPath.replace(/[\\/][^\\/]+$/, "");
    if (parent && parent !== rootPath) onRootChange(parent);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-1 px-2 py-2 border-b border-[var(--color-nexus-border)]">
        <span className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-nexus-muted)] flex-1 truncate">
          {rootPath.split(/[\\/]/).pop()}
        </span>
        <button onClick={goUp} className="p-1 rounded hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]" title="Subir">
          <FolderUp size={12} />
        </button>
        <button onClick={refresh} className="p-1 rounded hover:bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)]" title="Refrescar">
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1">
        {entries.map((entry) => (
          <TreeNode
            key={entry.path}
            entry={entry}
            depth={0}
            onFileSelect={onFileSelect}
            selectedFile={selectedFile}
          />
        ))}
        {entries.length === 0 && !loading && (
          <div className="px-3 py-4 text-xs text-[var(--color-nexus-muted)] text-center">
            Directorio vacío o no accesible
          </div>
        )}
      </div>
    </div>
  );
}
