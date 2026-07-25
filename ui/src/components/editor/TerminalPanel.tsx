import { useState, useRef, useEffect } from "react";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Terminal as TermIcon, Maximize2, Minimize2 } from "lucide-react";



interface TermLine {
  text: string;
  type: "input" | "output" | "error";
}

interface Props {
  cwd: string;
  expanded: boolean;
  onToggle: () => void;
}

export function TerminalPanel({ cwd, expanded, onToggle }: Props) {
  const [lines, setLines] = useState<TermLine[]>([
    { text: `SuperNEXUS Terminal — ${cwd}`, type: "output" },
  ]);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines.length]);

  useEffect(() => {
    if (expanded) inputRef.current?.focus();
  }, [expanded]);

  const execute = async () => {
    const cmd = input.trim();
    if (!cmd || running) return;
    setInput("");
    setLines((prev) => [...prev, { text: `$ ${cmd}`, type: "input" }]);
    setRunning(true);

    try {
      const res = await authFetch(`${API}/api/fs/exec`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd, cwd }),
      });
      const data = await res.json();
      if (data.stdout) {
        setLines((prev) => [...prev, { text: data.stdout, type: "output" }]);
      }
      if (data.stderr) {
        setLines((prev) => [...prev, { text: data.stderr, type: "error" }]);
      }
      if (data.error) {
        setLines((prev) => [...prev, { text: data.error, type: "error" }]);
      }
    } catch (err) {
      setLines((prev) => [
        ...prev,
        { text: `Error: ${err instanceof Error ? err.message : String(err)}`, type: "error" },
      ]);
    } finally {
      setRunning(false);
    }
  };

  if (!expanded) {
    return (
      <button
        onClick={onToggle}
        className="flex items-center gap-2 px-3 py-1.5 border-t border-[var(--color-nexus-border)] bg-[var(--color-nexus-surface)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)] text-xs transition-colors w-full"
      >
        <TermIcon size={12} />
        Terminal
        <Maximize2 size={10} className="ml-auto" />
      </button>
    );
  }

  return (
    <div className="flex flex-col border-t border-[var(--color-nexus-border)] bg-[#0a0e14]" style={{ height: 220 }}>
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--color-nexus-surface)] border-b border-[var(--color-nexus-border)]">
        <TermIcon size={12} className="text-[var(--color-nexus-accent)]" />
        <span className="text-[10px] font-mono text-[var(--color-nexus-muted)] flex-1">
          Terminal — {cwd.split(/[\\/]/).pop()}
        </span>
        <button
          onClick={() => setLines([])}
          className="text-[10px] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)] px-1"
        >
          Clear
        </button>
        <button onClick={onToggle} className="p-0.5 text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-text)]">
          <Minimize2 size={11} />
        </button>
      </div>

      {/* Output */}
      <div className="flex-1 overflow-y-auto px-3 py-2 font-mono text-[11px] leading-relaxed">
        {lines.map((line, i) => (
          <div
            key={i}
            className="whitespace-pre-wrap"
            style={{
              color:
                line.type === "input" ? "#8ffcff" :
                line.type === "error" ? "#ff5555" :
                "#b0b8c4",
            }}
          >
            {line.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex items-center gap-1 px-3 py-1.5 border-t border-[var(--color-nexus-border)]">
        <span className="text-[11px] font-mono text-[#8ffcff]">$</span>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && execute()}
          placeholder={running ? "Ejecutando..." : "Escribe un comando..."}
          disabled={running}
          className="flex-1 bg-transparent text-[11px] font-mono text-[#e0e0e0] placeholder:text-[#555] outline-none disabled:opacity-50"
        />
      </div>
    </div>
  );
}
