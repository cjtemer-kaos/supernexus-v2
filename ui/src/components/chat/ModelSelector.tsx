import { useAppStore } from "@/stores/appStore";
import { ChevronDown } from "lucide-react";
import { useState, useRef, useEffect } from "react";

export function ModelSelector() {
  const { availableModels, selectedModel, setSelectedModel } = useAppStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const current = availableModels.find((m) => m.id === selectedModel) || availableModels[0];

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-text-sub)] hover:text-[var(--color-nexus-text)] hover:bg-[var(--color-nexus-border)] transition-colors"
      >
        <span
          className="w-2 h-2 rounded-full"
          style={{ backgroundColor: current?.provider === "ollama" ? "var(--color-nexus-online)" : "var(--color-nexus-accent)" }}
        />
        <span className="max-w-[160px] truncate">{current?.name || "Seleccionar modelo"}</span>
        <ChevronDown size={12} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 w-64 z-50 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl shadow-xl overflow-hidden animate-nexus-in">
          <div className="px-3 py-2 border-b border-[var(--color-nexus-border)]">
            <span className="text-[10px] font-medium tracking-wider uppercase text-[var(--color-nexus-muted)]">
              Modelo para el Director
            </span>
          </div>
          <div className="max-h-60 overflow-y-auto py-1">
            {availableModels.map((m) => (
              <button
                key={m.id}
                onClick={() => { setSelectedModel(m.id); setOpen(false); }}
                className={`w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-[var(--color-nexus-surface-2)] transition-colors ${
                  m.id === selectedModel ? "bg-[var(--color-nexus-accent-bg)]" : ""
                }`}
              >
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: m.provider === "ollama" ? "var(--color-nexus-online)" : "var(--color-nexus-accent)" }}
                />
                <div className="min-w-0">
                  <div className="text-xs font-medium text-[var(--color-nexus-text)] truncate">{m.name}</div>
                  <div className="text-[10px] text-[var(--color-nexus-muted)] font-mono">{m.provider}</div>
                </div>
                {m.id === selectedModel && (
                  <span className="ml-auto text-[var(--color-nexus-accent)] text-xs">●</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
