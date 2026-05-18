import { useAppStore } from "@/stores/appStore";
import { GEMA_ICONS } from "@/components/home/HomeView";
import { ModelSelector } from "@/components/chat/ModelSelector";
import { Send, Diamond, Square } from "lucide-react";
import { useRef, useEffect } from "react";

export function ChatView() {
  const { chatMessages, chatInput, setChatInput, sendChatWS, stopStreaming, isStreaming, streamingContent, streamingGema, activeGema, gemas } = useAppStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const currentGema = gemas.find((g) => g.id === activeGema);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages.length, streamingContent]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) {
        stopStreaming();
      } else if (chatInput.trim()) {
        sendChatWS(chatInput);
        setChatInput("");
      }
    }
  };

  const handleSend = () => {
    if (isStreaming) {
      stopStreaming();
    } else if (chatInput.trim()) {
      sendChatWS(chatInput);
      setChatInput("");
    }
  };

  return (
    <div className="flex flex-col h-full animate-nexus-in">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 h-14 border-b border-[var(--color-nexus-border)] shrink-0">
        {currentGema ? (
          <>
            {(() => {
              const Icon = GEMA_ICONS[currentGema.name] || Diamond;
              return (
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${currentGema.color}15` }}
                >
                  <Icon size={16} style={{ color: currentGema.color }} />
                </div>
              );
            })()}
            <div>
              <div className="text-sm font-semibold text-[var(--color-nexus-text)]">{currentGema.name}</div>
              <div className="text-xs text-[var(--color-nexus-muted)] font-mono">{currentGema.model}</div>
            </div>
          </>
        ) : (
          <div className="text-sm font-semibold text-[var(--color-nexus-text)]">
            Chat con el Director
          </div>
        )}
        <div className="ml-auto">
          <ModelSelector />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {chatMessages.length === 0 && !streamingContent && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Diamond size={48} className="text-[var(--color-nexus-border)] mb-4" />
            <h2 className="text-lg font-semibold text-[var(--color-nexus-text)] mb-1">
              SuperNEXUS Chat
            </h2>
            <p className="text-sm text-[var(--color-nexus-text-sub)] max-w-md">
              Escribe un mensaje para hablar con el Director o selecciona una gema para interactuar directamente.
            </p>
          </div>
        )}

        {chatMessages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[70%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-[var(--color-nexus-accent-bg)] border border-[color-mix(in_srgb,var(--color-nexus-accent)_15%,transparent)] text-[var(--color-nexus-text)] rounded-br-sm"
                  : "bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] text-[var(--color-nexus-text)] rounded-bl-sm"
              }`}
            >
              {msg.gema && (
                <div className="flex items-center gap-1.5 mb-2">
                  {(() => {
                    const g = gemas.find((x) => x.id === `01-${msg.gema}` || x.name.toLowerCase() === msg.gema);
                    const Icon = g ? (GEMA_ICONS[g.name] || Diamond) : Diamond;
                    return (
                      <span
                        className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: g ? `${g.color}15` : "var(--color-nexus-surface-2)",
                          color: g?.color || "var(--color-nexus-accent)",
                        }}
                      >
                        <Icon size={12} />
                        {msg.gema}
                      </span>
                    );
                  })()}
                </div>
              )}
              <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <div className="flex justify-start">
            <div
              className="max-w-[70%] rounded-2xl px-4 py-3 text-sm bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] text-[var(--color-nexus-text)] rounded-bl-sm"
            >
              {streamingGema && (
                <div className="flex items-center gap-1.5 mb-2">
                  {(() => {
                    const g = gemas.find((x) => x.id === `01-${streamingGema}` || x.name.toLowerCase() === streamingGema);
                    const Icon = g ? (GEMA_ICONS[g.name] || Diamond) : Diamond;
                    return (
                      <span
                        className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: g ? `${g.color}15` : "var(--color-nexus-surface-2)",
                          color: g?.color || "var(--color-nexus-accent)",
                        }}
                      >
                        <Icon size={12} />
                        {streamingGema}
                      </span>
                    );
                  })()}
                </div>
              )}
              <div className="whitespace-pre-wrap leading-relaxed">
                {streamingContent}
                <span className="inline-block w-2 h-4 ml-1 bg-[var(--color-nexus-accent)] animate-pulse" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-6 pb-4 pt-2 border-t border-[var(--color-nexus-border)] shrink-0">
        <div className="flex items-end gap-2 bg-[var(--color-nexus-surface)] border border-[var(--color-nexus-border)] rounded-xl px-4 py-3 focus-within:border-[var(--color-nexus-accent)] transition-colors">
          <textarea
            ref={inputRef}
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isStreaming ? "Generando respuesta..." : "Escribe un mensaje... (Enter para enviar)"}
            rows={1}
            disabled={isStreaming}
            className="flex-1 bg-transparent text-sm text-[var(--color-nexus-text)] placeholder:text-[var(--color-nexus-muted)] outline-none resize-none max-h-32 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={!chatInput.trim() && !isStreaming}
            className="p-2 rounded-lg bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95"
          >
            {isStreaming ? <Square size={16} /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
