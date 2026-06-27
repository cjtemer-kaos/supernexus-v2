import { useState, useEffect } from "react";
import "./RealTimePanel.css";

interface HiveNode {
  name: string;
  host: string;
  status: string;
  capabilities: string[];
  last_seen: number;
}

interface HiveStatus {
  connected: boolean;
  running: boolean;
  nodes: Record<string, HiveNode>;
  pending_commands: number;
  registered_handlers: string[];
}

interface RealTimePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

function RealTimePanel({ isOpen, onClose }: RealTimePanelProps) {
  const [hiveStatus, setHiveStatus] = useState<HiveStatus | null>(null);
  const [command, setCommand] = useState("");
  const [targetNode, setTargetNode] = useState("");
  const [commandResult, setCommandResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"nodes" | "commands" | "mcp">("nodes");
  const [mcpTools, setMcpTools] = useState<any[]>([]);
  const [selectedTool, setSelectedTool] = useState("");
  const [toolArgs, setToolArgs] = useState("{}");
  const [toolResult, setToolResult] = useState("");

  useEffect(() => {
    if (isOpen) {
      loadHiveStatus();
      loadMcpTools();
      const interval = setInterval(loadHiveStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const loadHiveStatus = async () => {
    try {
      const res = await fetch("http://localhost:9000/api/hive/status");
      const data = await res.json();
      setHiveStatus(data);
    } catch {
      // Fallback
    }
  };

  const loadMcpTools = async () => {
    try {
      const res = await fetch("http://localhost:9000/api/mcp/tools");
      const data = await res.json();
      setMcpTools(data.tools || []);
    } catch {
      // Fallback
    }
  };

  const sendCommand = async () => {
    if (!command.trim()) return;
    setLoading(true);
    setCommandResult("");

    try {
      const res = await fetch("http://localhost:9000/api/hive/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          command,
          target: targetNode || null,
          timeout: 30,
        }),
      });
      const data = await res.json();
      setCommandResult(JSON.stringify(data, null, 2));
    } catch (error: any) {
      setCommandResult(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const executeMcpTool = async () => {
    if (!selectedTool) return;
    setLoading(true);
    setToolResult("");

    try {
      const args = JSON.parse(toolArgs);
      const res = await fetch("http://localhost:9000/api/mcp/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tool: selectedTool,
          arguments: args,
        }),
      });
      const data = await res.json();
      setToolResult(JSON.stringify(data, null, 2));
    } catch (error: any) {
      setToolResult(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const nodes = hiveStatus?.nodes || {};
  const nodeCount = Object.keys(nodes).length;
  const onlineNodes = Object.values(nodes).filter(n => n.status === "online").length;

  return (
    <div className="realtime-overlay" onClick={onClose}>
      <div className="realtime-panel" onClick={e => e.stopPropagation()}>
        <div className="realtime-header">
          <h2>📡 NexusHive - Comunicación en Tiempo Real</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="realtime-tabs">
          <button
            className={`tab ${activeTab === "nodes" ? "active" : ""}`}
            onClick={() => setActiveTab("nodes")}
          >
            🖥️ Nodos ({onlineNodes}/{nodeCount})
          </button>
          <button
            className={`tab ${activeTab === "commands" ? "active" : ""}`}
            onClick={() => setActiveTab("commands")}
          >
            ⚡ Comandos
          </button>
          <button
            className={`tab ${activeTab === "mcp" ? "active" : ""}`}
            onClick={() => setActiveTab("mcp")}
          >
            🔧 MCP Tools
          </button>
        </div>

        <div className="realtime-content">
          {activeTab === "nodes" && (
            <div className="nodes-section">
              <div className="hive-status">
                <div className="status-item">
                  <span className="status-label">Redis:</span>
                  <span className={`status-value ${hiveStatus?.connected ? "online" : "offline"}`}>
                    {hiveStatus?.connected ? "Conectado" : "Desconectado"}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">Hive:</span>
                  <span className={`status-value ${hiveStatus?.running ? "online" : "offline"}`}>
                    {hiveStatus?.running ? "Activo" : "Inactivo"}
                  </span>
                </div>
                <div className="status-item">
                  <span className="status-label">Handlers:</span>
                  <span className="status-value">{hiveStatus?.registered_handlers?.length || 0}</span>
                </div>
              </div>

              <div className="nodes-grid">
                {Object.entries(nodes).map(([id, node]) => (
                  <div key={id} className={`node-card ${node.status}`}>
                    <div className="node-header">
                      <span className="node-name">{node.name}</span>
                      <span className={`node-status ${node.status}`}>
                        {node.status === "online" ? "●" : "○"} {node.status}
                      </span>
                    </div>
                    <div className="node-info">
                      <span>Host: {node.host}</span>
                      <span>Capabilities: {node.capabilities.join(", ")}</span>
                      {node.last_seen > 0 && (
                        <span>Last seen: {new Date(node.last_seen * 1000).toLocaleTimeString()}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "commands" && (
            <div className="commands-section">
              <div className="command-form">
                <div className="form-group">
                  <label>Nodo destino (opcional)</label>
                  <select value={targetNode} onChange={e => setTargetNode(e.target.value)}>
                    <option value="">Broadcast (todos)</option>
                    {Object.entries(nodes).map(([id, node]) => (
                      <option key={id} value={id}>{node.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Comando</label>
                  <textarea
                    value={command}
                    onChange={e => setCommand(e.target.value)}
                    placeholder="Escribe el comando o tarea a ejecutar..."
                    rows={3}
                  />
                </div>
                <button
                  className="btn-send"
                  onClick={sendCommand}
                  disabled={loading || !command.trim()}
                >
                  {loading ? "Enviando..." : "Enviar Comando"}
                </button>
              </div>

              {commandResult && (
                <div className="command-result">
                  <h4>Resultado:</h4>
                  <pre>{commandResult}</pre>
                </div>
              )}
            </div>
          )}

          {activeTab === "mcp" && (
            <div className="mcp-section">
              <div className="tool-selector">
                <div className="form-group">
                  <label>Herramienta MCP</label>
                  <select value={selectedTool} onChange={e => setSelectedTool(e.target.value)}>
                    <option value="">Seleccionar herramienta...</option>
                    {mcpTools.map(tool => (
                      <option key={tool.name} value={tool.name}>
                        {tool.name} - {tool.description?.slice(0, 60)}...
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Argumentos (JSON)</label>
                  <textarea
                    value={toolArgs}
                    onChange={e => setToolArgs(e.target.value)}
                    placeholder='{"command": "whoami"}'
                    rows={4}
                  />
                </div>
                <button
                  className="btn-send"
                  onClick={executeMcpTool}
                  disabled={loading || !selectedTool}
                >
                  {loading ? "Ejecutando..." : "Ejecutar Herramienta"}
                </button>
              </div>

              {toolResult && (
                <div className="command-result">
                  <h4>Resultado MCP:</h4>
                  <pre>{toolResult}</pre>
                </div>
              )}

              <div className="tools-list">
                <h4>Herramientas Disponibles:</h4>
                {mcpTools.map(tool => (
                  <div key={tool.name} className="tool-item">
                    <span className="tool-name">{tool.name}</span>
                    <span className="tool-desc">{tool.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default RealTimePanel;
