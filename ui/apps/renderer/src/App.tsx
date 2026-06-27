import { useState, useEffect, useRef, useCallback } from "react";
import "./App.css";
import Sidebar from "./components/Sidebar";
import Chat from "./components/Chat";
import RightPanel from "./components/RightPanel";
import Settings from "./components/Settings";
import RealTimePanel from "./components/RealTimePanel";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  gem?: string;
  attachments?: string[];
}

interface SystemStats {
  cpu: number;
  memory: number;
  gpu: number;
  disk: number;
}

interface Gem {
  name: string;
  tags: string[];
  description: string;
  model: string;
  execution_count: number;
  success_rate: number;
}

function App() {
  const [backendOnline, setBackendOnline] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedGem, setSelectedGem] = useState("auto");
  const [selectedProject, setSelectedProject] = useState("default");
  const [selectedModel, setSelectedModel] = useState("qwen2.5-coder:7b");
  const [showSettings, setShowSettings] = useState(false);
  const [showRealTime, setShowRealTime] = useState(false);
  const [gems, setGems] = useState<Gem[]>([]);
  const [systemStats, setSystemStats] = useState<SystemStats>({ cpu: 0, memory: 0, gpu: 0, disk: 0 });
  const [dragOver, setDragOver] = useState(false);
  const [attachments, setAttachments] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const checkBackend = async () => {
      let retries = 3;
      while (retries > 0) {
        try {
          const status = await window.nexusAPI.status();
          setBackendOnline(status.online === true);
          return;
        } catch (error) {
          console.error("Backend check failed, retrying...", error);
          retries--;
          if (retries > 0) {
            await new Promise(r => setTimeout(r, 1000));
          }
        }
      }
      setBackendOnline(false);
    };
    checkBackend();
    const interval = setInterval(checkBackend, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const loadGems = async () => {
      try {
        const data = await window.nexusAPI.gems();
        if (data.gems) setGems(data.gems);
      } catch {
        // Fallback gems
        setGems([
          { name: "director", tags: ["leadership"], description: "Orquestacion", model: "", execution_count: 0, success_rate: 0 },
          { name: "code", tags: ["programming"], description: "Programacion", model: "", execution_count: 0, success_rate: 0 },
          { name: "scholar", tags: ["research"], description: "Investigacion", model: "", execution_count: 0, success_rate: 0 },
        ]);
      }
    };
    loadGems();
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const stats = await window.nexusAPI.systemStats();
        if (stats) {
          setSystemStats({
            cpu: stats.cpu || stats.cpu_usage || 0,
            memory: stats.memory || stats.ram_usage || 0,
            gpu: stats.gpu || stats.gpu_usage || 0,
            disk: stats.disk || stats.disk_usage || 0,
          });
        }
      } catch {
        // Fallback stats
        setSystemStats(prev => ({
          cpu: prev.cpu || 25,
          memory: prev.memory || 50,
          gpu: prev.gpu || 30,
          disk: prev.disk || 65,
        }));
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handlePaste = useCallback((e: ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    
    for (const item of items) {
      if (item.type.startsWith("image/")) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) {
          const reader = new FileReader();
          reader.onload = (event) => {
            if (event.target?.result) {
              setAttachments(prev => [...prev, event.target!.result as string]);
            }
          };
          reader.readAsDataURL(file);
        }
      }
    }
  }, []);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.addEventListener("paste", handlePaste);
      return () => textarea.removeEventListener("paste", handlePaste);
    }
  }, [handlePaste]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    
    const files = e.dataTransfer.files;
    for (const file of files) {
      if (file.type.startsWith("image/") || file.type.startsWith("text/") || file.name.endsWith(".py") || file.name.endsWith(".js") || file.name.endsWith(".ts")) {
        const reader = new FileReader();
        reader.onload = (event) => {
          if (event.target?.result) {
            setAttachments(prev => [...prev, event.target!.result as string]);
          }
        };
        reader.readAsDataURL(file);
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    
    for (const file of files) {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          setAttachments(prev => [...prev, event.target!.result as string]);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  const handleSend = async () => {
    if ((!input.trim() && attachments.length === 0) || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date().toISOString(),
      attachments: attachments.length > 0 ? [...attachments] : undefined,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setAttachments([]);
    setLoading(true);

    try {
      const response = await window.nexusAPI.chat(input, selectedGem, selectedProject, undefined, attachments);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.content || "Error al procesar",
        timestamp: new Date().toISOString(),
        gem: response.gem,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "system",
        content: "Error de conexión con el backend",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const openAvatarWindow = () => {
    window.nexusAPI.openAvatarWindow();
  };

  return (
    <div className="app">
      <Sidebar
        selectedGem={selectedGem}
        onGemChange={setSelectedGem}
        selectedProject={selectedProject}
        onProjectChange={setSelectedProject}
        backendOnline={backendOnline}
        gems={gems}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        onOpenSettings={() => setShowSettings(true)}
      />

      <div className="main-content">
        <div className="toolbar">
          <div className="toolbar-left">
            <button className="avatar-btn" onClick={openAvatarWindow} title="Abrir ventana del avatar">
              🎭 Avatar
            </button>
            <button className="avatar-btn" onClick={() => setShowRealTime(true)} title="Comunicación en tiempo real">
              📡 NexusHive
            </button>
          </div>
          
          <div className="toolbar-center">
            <div className="status-indicator">
              <span className={`status-dot ${backendOnline ? "online" : "offline"}`} />
              <span className="status-text">{backendOnline ? "NEXUS Online" : "NEXUS Offline"}</span>
            </div>
          </div>

          <div className="toolbar-right">
            <div className="system-monitor">
              <div className="stat-item" title={`CPU: ${systemStats.cpu.toFixed(1)}%`}>
                <span className="stat-icon">🖥️</span>
                <div className="stat-bar">
                  <div className="stat-fill" style={{ width: `${Math.min(systemStats.cpu, 100)}%`, background: systemStats.cpu > 80 ? "#ef4444" : systemStats.cpu > 60 ? "#f97316" : "#22c55e" }} />
                </div>
                <span className="stat-value">{systemStats.cpu.toFixed(0)}%</span>
              </div>
              <div className="stat-item" title={`RAM: ${systemStats.memory.toFixed(1)}%`}>
                <span className="stat-icon">💾</span>
                <div className="stat-bar">
                  <div className="stat-fill" style={{ width: `${Math.min(systemStats.memory, 100)}%`, background: systemStats.memory > 80 ? "#ef4444" : systemStats.memory > 60 ? "#f97316" : "#3b82f6" }} />
                </div>
                <span className="stat-value">{systemStats.memory.toFixed(0)}%</span>
              </div>
              <div className="stat-item" title={`GPU: ${systemStats.gpu.toFixed(1)}%`}>
                <span className="stat-icon">🎮</span>
                <div className="stat-bar">
                  <div className="stat-fill" style={{ width: `${Math.min(systemStats.gpu, 100)}%`, background: systemStats.gpu > 80 ? "#ef4444" : systemStats.gpu > 60 ? "#f97316" : "#8b5cf6" }} />
                </div>
                <span className="stat-value">{systemStats.gpu.toFixed(0)}%</span>
              </div>
              <div className="stat-item" title={`Disco: ${systemStats.disk.toFixed(1)}%`}>
                <span className="stat-icon">💿</span>
                <div className="stat-bar">
                  <div className="stat-fill" style={{ width: `${Math.min(systemStats.disk, 100)}%`, background: systemStats.disk > 80 ? "#ef4444" : systemStats.disk > 60 ? "#f97316" : "#eab308" }} />
                </div>
                <span className="stat-value">{systemStats.disk.toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </div>

        <div 
          className={`chat-container ${dragOver ? "drag-over" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {dragOver && (
            <div className="drag-overlay">
              <div className="drag-content">
                <span className="drag-icon">📁</span>
                <p>Suelta archivos aquí para adjuntarlos</p>
              </div>
            </div>
          )}
          
          <Chat
            messages={messages}
            loading={loading}
            chatEndRef={chatEndRef}
          />

          {attachments.length > 0 && (
            <div className="attachments-bar">
              {attachments.map((att, index) => (
                <div key={index} className="attachment-item">
                  {att.startsWith("data:image") ? (
                    <img src={att} alt={`Attachment ${index + 1}`} className="attachment-thumb" />
                  ) : (
                    <span className="attachment-icon">📄</span>
                  )}
                  <button className="attachment-remove" onClick={() => removeAttachment(index)}>×</button>
                </div>
              ))}
            </div>
          )}

          <div className="input-area">
            <div className="input-actions">
              <button 
                className="action-btn" 
                onClick={() => fileInputRef.current?.click()}
                title="Adjuntar archivo (Ctrl+V para imágenes, arrastra archivos aquí)"
              >
                📎
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.txt,.py,.js,.ts,.json,.md"
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
            </div>
            <div className="input-wrapper">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Escribe tu mensaje... (Enter para enviar, Shift+Enter para nueva línea, Ctrl+V para pegar imágenes)"
                rows={1}
              />
              <button className="send-btn" onClick={handleSend} disabled={loading || (!input.trim() && attachments.length === 0)}>
                {loading ? "⏳" : "Enviar"}
              </button>
            </div>
          </div>
        </div>
      </div>

      <RightPanel />

      {showSettings && <Settings onClose={() => setShowSettings(false)} />}
    </div>
  );
}

export default App;
