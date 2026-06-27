import { useAppStore } from "@/stores/appStore";
import { GEMA_ICONS } from "@/components/home/HomeView";
import { ModelSelector } from "@/components/chat/ModelSelector";
import { API } from "@/api/config";
import { authFetch } from "@/api/nexus";
import { Send, Diamond, Square, Mic, MicOff, User, Paperclip, X, Image, Volume2, VolumeX } from "lucide-react";
import { useRef, useEffect, useCallback, useState } from "react";
import { createPortal } from "react-dom";
import { AvatarWindow } from "@/components/chat/AvatarWindow";

export function ChatView() {
  const { chatMessages, chatInput, setChatInput, sendChatWS, stopStreaming, isStreaming, streamingContent, streamingGema, activeGema, gemas, isListening, setIsListening, voiceEnabled, setVoiceEnabled, avatarOpen, setAvatarOpen, pendingImages, setPendingImages } = useAppStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const currentGema = gemas.find((g) => g.id === activeGema);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages.length, streamingContent, pendingImages.length]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handlePaste = useCallback(async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const blob = item.getAsFile();
        if (!blob) continue;

        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result as string;
          setPendingImages([...pendingImages, base64]);
        };
        reader.readAsDataURL(blob);
        break;
      }
    }
  }, [pendingImages, setPendingImages]);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    const imageFiles = files.filter((f) => f.type.startsWith("image/"));

    for (const file of imageFiles) {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        setPendingImages([...pendingImages, base64]);
      };
      reader.readAsDataURL(file);
    }
  }, [pendingImages, setPendingImages]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const file of files) {
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result as string;
          setPendingImages([...pendingImages, base64]);
        };
        reader.readAsDataURL(file);
      }
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [pendingImages, setPendingImages]);

  const removePendingImage = (index: number) => {
    setPendingImages(pendingImages.filter((_, i) => i !== index));
  };

  const startListening = useCallback(async () => {
    if (!voiceEnabled) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());

        if (audioBlob.size === 0) return;

        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");
        formData.append("language", "es");

        try {
          const res = await authFetch(`${API}/api/voice/transcribe`, {
            method: "POST",
            body: formData,
          });
          const data = await res.json();
          if (data.text && data.text.trim()) {
            setChatInput(data.text.trim());
            setTimeout(() => sendChatWS(data.text.trim()), 100);
          }
        } catch (err) {
          console.error("Error transcribiendo:", err);
        }
      };

      mediaRecorder.start();
      setIsListening(true);
    } catch (err) {
      console.error("Error accediendo al microfono:", err);
    }
  }, [voiceEnabled, setIsListening, setChatInput, sendChatWS]);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    setIsListening(false);
  }, [setIsListening]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) {
        stopStreaming();
      } else if (chatInput.trim() || pendingImages.length > 0) {
        const hasImages = pendingImages.length > 0;
        sendChatWS(chatInput.trim(), undefined, hasImages ? pendingImages : undefined);
      }
    }
  };

  const handleSend = () => {
    if (isStreaming) {
      stopStreaming();
    } else if (chatInput.trim() || pendingImages.length > 0) {
      const hasImages = pendingImages.length > 0;
      sendChatWS(chatInput.trim(), undefined, hasImages ? pendingImages : undefined);
    }
  };

  return (
    <div
      className="flex flex-col h-full animate-nexus-in"
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onPaste={handlePaste}
    >
      {/* Compact Header for Model Selector */}
      <div className="flex items-center justify-between px-6 py-2 shrink-0">
        <div className="text-sm font-semibold text-[var(--color-nexus-text)]">
          {currentGema ? currentGema.name : "Chat con el Director"}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAvatarOpen(true)}
            className="p-1.5 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent-bg)] transition-all active:scale-95"
            title="Abrir Avatar del Director"
          >
            <User size={14} />
          </button>
          <ModelSelector />
          <button
            onClick={() => setVoiceEnabled(!voiceEnabled)}
            className={`p-1.5 rounded-lg transition-all active:scale-95 ${
              voiceEnabled
                ? "bg-red-500/20 text-red-400 hover:bg-red-500/30"
                : "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
            }`}
            title={voiceEnabled ? "Voz activa (click para silenciar)" : "Voz silenciada (click para activar)"}
          >
            {voiceEnabled ? <Volume2 size={14} /> : <VolumeX size={14} />}
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {chatMessages.length === 0 && !streamingContent && pendingImages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Diamond size={48} className="text-[var(--color-nexus-border)] mb-4" />
            <h2 className="text-lg font-semibold text-[var(--color-nexus-text)] mb-1">
              SuperNEXUS Chat
            </h2>
            <p className="text-sm text-[var(--color-nexus-text-sub)] max-w-md">
              Escribe un mensaje para hablar con el Director o selecciona una gema para interactuar directamente.
            </p>
            <p className="text-xs text-[var(--color-nexus-muted)] mt-2">
              Arrastra imagenes aqui o usa Ctrl+V para pegar
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
              {msg.images && msg.images.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {msg.images.map((img, idx) => (
                    <img
                      key={idx}
                      src={img}
                      alt={`Imagen ${idx + 1}`}
                      className="max-w-[200px] max-h-[150px] rounded-lg object-contain border border-[var(--color-nexus-border)]"
                    />
                  ))}
                </div>
              )}
              <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
              {msg.role === "assistant" && !voiceEnabled && (
                <button
                  onClick={async () => {
                    try {
                      const res = await authFetch(`${API}/api/voice/speak`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json", "Accept": "audio/wav" },
                        body: JSON.stringify({ text: msg.content, return_audio: true }),
                      });
                      if (res.ok) {
                        const blob = await res.blob();
                        const url = URL.createObjectURL(blob);
                        const audio = new Audio(url);
                        audio.play();
                        audio.onended = () => URL.revokeObjectURL(url);
                      }
                    } catch {}
                  }}
                  className="mt-2 p-1 rounded-md hover:bg-[var(--color-nexus-accent-bg)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)] transition-colors"
                  title="Escuchar respuesta"
                >
                  <Volume2 size={14} />
                </button>
              )}
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

      {/* Pending images preview */}
      {pendingImages.length > 0 && (
        <div className="px-6 py-2 border-t border-[var(--color-nexus-border)] shrink-0">
          <div className="flex flex-wrap gap-2">
            {pendingImages.map((img, idx) => (
              <div key={idx} className="relative group">
                <img
                  src={img}
                  alt={`Preview ${idx + 1}`}
                  className="w-16 h-16 rounded-lg object-cover border border-[var(--color-nexus-border)]"
                />
                <button
                  onClick={() => removePendingImage(idx)}
                  className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-6 pb-4 pt-2 border-t border-[var(--color-nexus-border)] shrink-0">
        <div
          className={`flex items-end gap-2 bg-[var(--color-nexus-surface)] border rounded-xl px-4 py-3 transition-colors ${
            isDragOver
              ? "border-[var(--color-nexus-accent)] shadow-[0_0_12px_var(--color-nexus-accent)] bg-[var(--color-nexus-accent-bg)]"
              : isListening
              ? "border-[var(--color-nexus-accent)] shadow-[0_0_12px_var(--color-nexus-accent)]"
              : "border-[var(--color-nexus-border)] focus-within:border-[var(--color-nexus-accent)]"
          }`}
          onKeyDown={handleKeyDown}
        >
          <button
            onClick={handleFileSelect}
            className="p-2 rounded-lg bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)] hover:bg-[var(--color-nexus-accent-bg)] transition-all active:scale-95 shrink-0"
            title="Adjuntar imagen"
          >
            <Paperclip size={16} />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onMouseDown={startListening}
            onMouseUp={stopListening}
            onMouseLeave={stopListening}
            disabled={!voiceEnabled}
            className={`p-2 rounded-lg transition-all shrink-0 ${
              isListening
                ? "bg-red-500/20 text-red-400 animate-pulse"
                : "bg-[var(--color-nexus-surface-2)] text-[var(--color-nexus-muted)] hover:text-[var(--color-nexus-accent)]"
            } disabled:opacity-30 disabled:cursor-not-allowed`}
            title={isListening ? "Soltar para enviar" : "Mantener para hablar (o presiona espacio)"}
          >
            {isListening ? <MicOff size={16} /> : <Mic size={16} />}
          </button>
          <textarea
            ref={inputRef}
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={
              isListening
                ? "Escuchando... suelta para enviar"
                : isStreaming
                ? "Generando respuesta..."
                : pendingImages.length > 0
                ? "Escribe un mensaje sobre la imagen... (Enter para enviar)"
                : "Escribe un mensaje... [SPACE=VOZ] (Enter para enviar, Ctrl+V para imagen)"
            }
            rows={1}
            disabled={isStreaming || isListening}
            className="flex-1 bg-transparent text-sm text-[var(--color-nexus-text)] placeholder:text-[var(--color-nexus-muted)] outline-none resize-none max-h-32 disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={(!chatInput.trim() && pendingImages.length === 0 && !isStreaming) || isListening}
            className="p-2 rounded-lg bg-[var(--color-nexus-accent)] text-white hover:bg-[var(--color-nexus-accent-dim)] disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95"
          >
            {isStreaming ? <Square size={16} /> : <Send size={16} />}
          </button>
        </div>
        {isListening && (
          <div className="flex items-center gap-2 mt-2 text-xs text-red-400 animate-pulse">
            <Mic size={12} />
            <span>Escuchando... suelta Espacio o el boton para enviar</span>
          </div>
        )}
        {isDragOver && (
          <div className="flex items-center gap-2 mt-2 text-xs text-[var(--color-nexus-accent)]">
            <Image size={12} />
            <span>Suelta las imagenes aqui</span>
          </div>
        )}
      </div>
      {/* Avatar Window */}
      {avatarOpen && createPortal(
        <AvatarWindow onClose={() => setAvatarOpen(false)} />,
        document.body
      )}
    </div>
  );
}
