import { useState, useEffect } from "react";
import "./RightPanel.css";

function RightPanel() {
  const [activeTab, setActiveTab] = useState<"tools" | "memory" | "graph" | "tailscale" | "settings">("tools");
  const [memorySearch, setMemorySearch] = useState("");
  const [memoryResults, setMemoryResults] = useState<any[]>([]);
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({
    nodes: [],
    edges: [],
  });
  const [tailscaleNodes, setTailscaleNodes] = useState<any[]>([]);
  const [systemStatus, setSystemStatus] = useState<any>(null);

  useEffect(() => {
    if (activeTab === "graph") {
      loadGraph();
    } else if (activeTab === "tailscale") {
      loadTailscale();
    } else if (activeTab === "settings") {
      loadStatus();
    }
  }, [activeTab]);

  const loadGraph = async () => {
    try {
      const data = await window.nexusAPI.knowledgeGraph();
      setGraphData(data);
    } catch {
      // Use empty
    }
  };

  const loadTailscale = async () => {
    try {
      const data = await window.nexusAPI.tailscaleNodes();
      setTailscaleNodes(data.nodes || []);
    } catch {
      setTailscaleNodes([]);
    }
  };

  const loadStatus = async () => {
    try {
      const data = await window.nexusAPI.status();
      setSystemStatus(data);
    } catch {
      setSystemStatus(null);
    }
  };

  const searchMemory = async () => {
    if (!memorySearch.trim()) return;
    try {
      const results = await window.nexusAPI.memorySearch(memorySearch);
      setMemoryResults(results.results || []);
    } catch {
      setMemoryResults([]);
    }
  };

  return (
    <aside className="right-panel">
      <div className="panel-tabs">
        <button
          className={activeTab === "tools" ? "active" : ""}
          onClick={() => setActiveTab("tools")}
        >
          Tools
        </button>
        <button
          className={activeTab === "memory" ? "active" : ""}
          onClick={() => setActiveTab("memory")}
        >
          Memory
        </button>
        <button
          className={activeTab === "graph" ? "active" : ""}
          onClick={() => setActiveTab("graph")}
        >
          Graph
        </button>
        <button
          className={activeTab === "tailscale" ? "active" : ""}
          onClick={() => setActiveTab("tailscale")}
        >
          Tailscale
        </button>
        <button
          className={activeTab === "settings" ? "active" : ""}
          onClick={() => setActiveTab("settings")}
        >
          Settings
        </button>
      </div>

      <div className="panel-content">
        {activeTab === "tools" && (
          <div className="tools-panel">
            <h3>Tools Activos</h3>
            <ul>
              <li>Workspace CRUD</li>
              <li>Execute Command</li>
              <li>Parse File</li>
              <li>SSH Bridge</li>
              <li>Tailscale Bridge</li>
              <li>MCP Chat</li>
              <li>PC2 Bridge</li>
              <li>Ollama LLM</li>
            </ul>
          </div>
        )}

        {activeTab === "memory" && (
          <div className="memory-panel">
            <h3>Busqueda Semantica</h3>
            <div className="memory-search">
              <input
                type="text"
                value={memorySearch}
                onChange={(e) => setMemorySearch(e.target.value)}
                placeholder="Buscar en memoria..."
                onKeyDown={(e) => e.key === "Enter" && searchMemory()}
              />
              <button onClick={searchMemory}>Buscar</button>
            </div>
            <div className="memory-results">
              {memoryResults.map((r: any, i: number) => (
                <div key={i} className="memory-result">
                  <div className="result-score">
                    {(r.score * 100).toFixed(0)}%
                  </div>
                  <div className="result-preview">{r.preview}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "graph" && (
          <div className="graph-panel">
            <h3>Knowledge Graph</h3>
            <div className="graph-stats">
              <p>Nodos: {graphData.nodes?.length || 0}</p>
              <p>Conexiones: {graphData.edges?.length || 0}</p>
            </div>
            <div className="graph-visualization">
              {graphData.nodes?.length === 0 ? (
                <p className="empty-state">
                  No hay nodos en el grafo aun.
                </p>
              ) : (
                <ul>
                  {graphData.nodes.slice(0, 20).map((n: any, i: number) => (
                    <li key={i}>
                      {n.name || n.id} ({n.category || "unknown"})
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {activeTab === "tailscale" && (
          <div className="tailscale-panel">
            <h3>Tailscale Nodes</h3>
            <div className="tailscale-status">
              <p>Acceso global seguro a todos los nodos</p>
            </div>
            <div className="tailscale-nodes">
              {tailscaleNodes.length === 0 ? (
                <p className="empty-state">
                  No hay nodos de Tailscale disponibles.
                </p>
              ) : (
                <ul>
                  {tailscaleNodes.map((n: any, i: number) => (
                    <li key={i} className="tailscale-node">
                      <div className="node-name">{n.name || n.hostname}</div>
                      <div className="node-ip">{n.ip}</div>
                      <div className={`node-status ${n.online ? "online" : "offline"}`}>
                        {n.online ? "Online" : "Offline"}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <div className="settings-panel">
            <h3>System Status</h3>
            {systemStatus ? (
              <div className="settings-content">
                <div className="setting-group">
                  <h4>Director</h4>
                  <p>Version: {systemStatus.version || "2.0"}</p>
                  <p>Project: {systemStatus.director?.current_project || "default"}</p>
                  <p>Gems: {systemStatus.director?.gemas_count || 15}</p>
                </div>
                <div className="setting-group">
                  <h4>Engines</h4>
                  {Object.entries(systemStatus.engines || {}).map(([name, state]: [string, any]) => (
                    <p key={name}>
                      {name}: <span className={state === "online" ? "status-ok" : "status-error"}>{state}</span>
                    </p>
                  ))}
                </div>
                <div className="setting-group">
                  <h4>Memory</h4>
                  <p>Neural: {systemStatus.memory?.neural?.total_patterns || 0} patterns</p>
                  <p>RAG: {systemStatus.memory?.rag?.total_entries || 0} entries</p>
                  <p>Graph: {systemStatus.memory?.graph?.total_notes || 0} notes</p>
                </div>
                <div className="setting-group">
                  <h4>PC2</h4>
                  <p>Host: {systemStatus.pc2?.host || "Configure Host"}</p>
                  <p>Status: <span className={systemStatus.pc2?.online ? "status-ok" : "status-error"}>
                    {systemStatus.pc2?.online ? "Online" : "Offline"}
                  </span></p>
                </div>
              </div>
            ) : (
              <p className="empty-state">Loading status...</p>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

export default RightPanel;
