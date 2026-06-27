import { useState, useEffect } from "react";
import "./Settings.css";

interface ApiConfig {
  provider: string;
  enabled: boolean;
  apiKey: string;
  baseUrl: string;
  defaultModel: string;
  models: string[];
}

interface SettingsProps {
  onClose: () => void;
}

function Settings({ onClose }: SettingsProps) {
  const [activeTab, setActiveTab] = useState("models");
  const [selectedModel, setSelectedModel] = useState("qwen2.5-coder:7b");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [apiConfigs, setApiConfigs] = useState<ApiConfig[]>([
    {
      provider: "openai",
      enabled: false,
      apiKey: "",
      baseUrl: "https://api.openai.com/v1",
      defaultModel: "gpt-4o",
      models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    {
      provider: "anthropic",
      enabled: false,
      apiKey: "",
      baseUrl: "https://api.anthropic.com",
      defaultModel: "claude-sonnet-4-20250514",
      models: ["claude-sonnet-4-20250514", "claude-opus-4-20250414", "claude-haiku-3-5-20250414"],
    },
    {
      provider: "google",
      enabled: false,
      apiKey: "",
      baseUrl: "https://generativelanguage.googleapis.com/v1beta",
      defaultModel: "gemini-2.5-pro",
      models: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    },
    {
      provider: "groq",
      enabled: false,
      apiKey: "",
      baseUrl: "https://api.groq.com/openai/v1",
      defaultModel: "llama-3.3-70b-versatile",
      models: ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
    },
    {
      provider: "openrouter",
      enabled: false,
      apiKey: "",
      baseUrl: "https://openrouter.ai/api/v1",
      defaultModel: "meta-llama/llama-3.3-70b-instruct",
      models: ["meta-llama/llama-3.3-70b-instruct", "mistralai/mixtral-8x7b-instruct", "google/gemini-2.5-pro"],
    },
    {
      provider: "deepseek",
      enabled: false,
      apiKey: "",
      baseUrl: "https://api.deepseek.com/v1",
      defaultModel: "deepseek-chat",
      models: ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
    },
  ]);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const config = await window.nexusAPI.getConfig();
      if (config) {
        if (config.defaultModel) setSelectedModel(config.defaultModel);
        if (config.ollamaUrl) setOllamaUrl(config.ollamaUrl);
        if (config.apiProviders) {
          setApiConfigs(prev =>
            prev.map(cfg => {
              const saved = config.apiProviders[cfg.provider];
              return saved ? { ...cfg, ...saved } : cfg;
            })
          );
        }
      }
    } catch {
      // Use defaults
    }
  };

  const saveSettings = async () => {
    try {
      const config = {
        defaultModel: selectedModel,
        ollamaUrl,
        apiProviders: apiConfigs.reduce((acc, cfg) => {
          acc[cfg.provider] = {
            enabled: cfg.enabled,
            apiKey: cfg.apiKey,
            baseUrl: cfg.baseUrl,
            defaultModel: cfg.defaultModel,
          };
          return acc;
        }, {} as Record<string, any>),
      };
      await window.nexusAPI.setConfig(config);
      onClose();
    } catch (error) {
      console.error("Error saving settings:", error);
    }
  };

  const updateApiConfig = (index: number, field: keyof ApiConfig, value: any) => {
    setApiConfigs(prev => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={e => e.stopPropagation()}>
        <div className="settings-header">
          <h2>⚙️ Configuración</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="settings-tabs">
          <button
            className={`tab ${activeTab === "models" ? "active" : ""}`}
            onClick={() => setActiveTab("models")}
          >
            🧠 Modelo IA
          </button>
          <button
            className={`tab ${activeTab === "apis" ? "active" : ""}`}
            onClick={() => setActiveTab("apis")}
          >
            🔌 APIs Externas
          </button>
          <button
            className={`tab ${activeTab === "voice" ? "active" : ""}`}
            onClick={() => setActiveTab("voice")}
          >
            🎭 Voz
          </button>
        </div>

        <div className="settings-content">
          {activeTab === "models" && (
            <div className="settings-section">
              <h3>Cerebro del Director IA</h3>
              <div className="setting-group">
                <label>Motor de IA por defecto</label>
                <select
                  value={selectedModel}
                  onChange={e => setSelectedModel(e.target.value)}
                  className="model-select"
                >
                  <optgroup label="Local (Ollama)">
                    <option value="qwen2.5-coder:7b">qwen2.5-coder:7b</option>
                    <option value="qwen2.5:7b">qwen2.5:7b</option>
                    <option value="llama3.2:3b">llama3.2:3b</option>
                    <option value="mistral:7b">mistral:7b</option>
                    <option value="phi4:14b">phi4:14b</option>
                    <option value="deepseek-r1:7b">deepseek-r1:7b</option>
                  </optgroup>
                  <optgroup label="APIs Externas (requieren configuración)">
                    {apiConfigs
                      .filter(cfg => cfg.enabled)
                      .flatMap(cfg =>
                        cfg.models.map(m => (
                          <option key={m} value={m}>
                            {cfg.provider.toUpperCase()} - {m}
                          </option>
                        ))
                      )}
                  </optgroup>
                </select>
              </div>

              <div className="setting-group">
                <label>URL de Ollama</label>
                <input
                  type="text"
                  value={ollamaUrl}
                  onChange={e => setOllamaUrl(e.target.value)}
                  placeholder="http://localhost:11434"
                />
              </div>

              <div className="setting-info">
                <p>💡 Los modelos locales se ejecutan en tu máquina sin costo. Las APIs externas ofrecen mayor capacidad pero requieren claves de API.</p>
              </div>
            </div>
          )}

          {activeTab === "apis" && (
            <div className="settings-section">
              <h3>APIs Externas de IA</h3>
              <p className="section-desc">Configura proveedores de IA externos para usar cuando el modelo local no sea suficiente.</p>

              {apiConfigs.map((cfg, index) => (
                <div key={cfg.provider} className="api-provider">
                  <div className="api-header">
                    <div className="api-title">
                      <span className="api-icon">
                        {cfg.provider === "openai" && "🟢"}
                        {cfg.provider === "anthropic" && "🟣"}
                        {cfg.provider === "google" && "🔵"}
                        {cfg.provider === "groq" && "⚡"}
                        {cfg.provider === "openrouter" && "🌐"}
                        {cfg.provider === "deepseek" && "🔷"}
                      </span>
                      <span className="api-name">{cfg.provider.toUpperCase()}</span>
                    </div>
                    <label className="toggle-switch">
                      <input
                        type="checkbox"
                        checked={cfg.enabled}
                        onChange={e => updateApiConfig(index, "enabled", e.target.checked)}
                      />
                      <span className="slider"></span>
                    </label>
                  </div>

                  {cfg.enabled && (
                    <div className="api-fields">
                      <div className="field">
                        <label>API Key</label>
                        <input
                          type="password"
                          value={cfg.apiKey}
                          onChange={e => updateApiConfig(index, "apiKey", e.target.value)}
                          placeholder="sk-..."
                        />
                      </div>
                      <div className="field">
                        <label>Base URL</label>
                        <input
                          type="text"
                          value={cfg.baseUrl}
                          onChange={e => updateApiConfig(index, "baseUrl", e.target.value)}
                        />
                      </div>
                      <div className="field">
                        <label>Modelo por defecto</label>
                        <select
                          value={cfg.defaultModel}
                          onChange={e => updateApiConfig(index, "defaultModel", e.target.value)}
                        >
                          {cfg.models.map(m => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === "voice" && (
            <div className="settings-section">
              <h3>Configuración de Voz</h3>
              <div className="setting-group">
                <label>Motor de TTS</label>
                <select className="model-select">
                  <option value="edge">Edge TTS (Recomendado)</option>
                  <option value="pyttsx3">pyttsx3 (Local)</option>
                  <option value="elevenlabs">ElevenLabs (API)</option>
                </select>
              </div>
              <div className="setting-group">
                <label>Motor de STT</label>
                <select className="model-select">
                  <option value="whisper">Whisper (Local)</option>
                  <option value="whisper-api">Whisper API (OpenAI)</option>
                </select>
              </div>
            </div>
          )}
        </div>

        <div className="settings-footer">
          <button className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" onClick={saveSettings}>Guardar</button>
        </div>
      </div>
    </div>
  );
}

export default Settings;
