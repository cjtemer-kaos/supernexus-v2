import { useState, useEffect } from "react";
import "./Sidebar.css";

interface Gem {
  name: string;
  tags: string[];
  description: string;
  model: string;
  execution_count: number;
  success_rate: number;
}

interface SidebarProps {
  selectedGem: string;
  onGemChange: (gem: string) => void;
  selectedProject: string;
  onProjectChange: (project: string) => void;
  backendOnline: boolean;
  gems?: Gem[];
  selectedModel: string;
  onModelChange: (model: string) => void;
  onOpenSettings: () => void;
}

const GEM_ICONS: Record<string, string> = {
  director: "🧠",
  code: "💻",
  scholar: "",
  architect: "🏗️",
  creative: "🎨",
  sage: "🧙",
  analyst: "📊",
  engineer: "",
  debugger: "🐛",
  optimizer: "⚡",
  tester: "🧪",
  security: "️",
  devops: "🚀",
  trainer: "",
  biblioteca: "📖",
  vision: "👁️",
  opencode: "🖥️",
  codex: "📝",
  design: "🎬",
  music: "",
  prompter: "✏️",
  producer: "📅",
};

function Sidebar({
  selectedGem,
  onGemChange,
  selectedProject,
  onProjectChange,
  backendOnline,
  gems = [],
  selectedModel,
  onModelChange,
  onOpenSettings,
}: SidebarProps) {
  const [projects, setProjects] = useState<string[]>(["default"]);
  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [searchFilter, setSearchFilter] = useState("");

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await window.nexusAPI.projects();
      if (data.projects?.length > 0) {
        setProjects(data.projects);
      }
    } catch {
      // Use default
    }
  };

  const createProject = async () => {
    if (!newProjectName.trim()) return;
    setProjects((prev) => [...prev, newProjectName]);
    onProjectChange(newProjectName);
    setNewProjectName("");
    setShowNewProject(false);
  };

  const displayGems = gems.length > 0 ? gems : [];
  const filteredGems = displayGems.filter(gem => 
    gem.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
    gem.description.toLowerCase().includes(searchFilter.toLowerCase()) ||
    gem.tags.some(tag => tag.toLowerCase().includes(searchFilter.toLowerCase()))
  );

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">🧠</span>
          <h1>NEXUS IA</h1>
        </div>
        <div className={`status ${backendOnline ? "online" : "offline"}`}>
          <span className="status-dot" />
          {backendOnline ? "Online" : "Offline"}
        </div>
      </div>

      <div className="sidebar-section">
        <h3>Cerebro del Director</h3>
        <select
          value={selectedModel}
          onChange={e => onModelChange(e.target.value)}
          className="model-select"
        >
          <option value="qwen2.5-coder:7b">qwen2.5-coder:7b</option>
          <option value="qwen2.5:7b">qwen2.5:7b</option>
          <option value="llama3.2:3b">llama3.2:3b</option>
          <option value="mistral:7b">mistral:7b</option>
          <option value="phi4:14b">phi4:14b</option>
          <option value="deepseek-r1:7b">deepseek-r1:7b</option>
        </select>
      </div>

      <div className="sidebar-section">
        <h3>Proyecto</h3>
        <select
          value={selectedProject}
          onChange={(e) => onProjectChange(e.target.value)}
          className="project-select"
        >
          {projects.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        {showNewProject ? (
          <div className="new-project-form">
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Nombre del proyecto"
              onKeyDown={(e) => e.key === "Enter" && createProject()}
            />
            <button onClick={createProject}>Crear</button>
            <button onClick={() => setShowNewProject(false)}>Cancelar</button>
          </div>
        ) : (
          <button
            className="btn-small"
            onClick={() => setShowNewProject(true)}
          >
            + Nuevo proyecto
          </button>
        )}
      </div>

      <div className="sidebar-section">
        <h3>Director IA (Gemas)</h3>
        <input
          type="text"
          className="gem-search"
          placeholder="Buscar gema..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
        />
        <div className="gem-list">
          <button
            className={`gem-item ${selectedGem === "auto" ? "active" : ""}`}
            onClick={() => onGemChange("auto")}
            title="Routing automatico del Director"
          >
            <span className="gem-icon">🧠</span>
            <span className="gem-name">Auto (Director)</span>
          </button>
          {filteredGems.map((gem) => (
            <button
              key={gem.name}
              className={`gem-item ${selectedGem === gem.name ? "active" : ""}`}
              onClick={() => onGemChange(gem.name)}
              title={`${gem.description} | Modelo: ${gem.model || "auto"}`}
            >
              <span className="gem-icon">{GEM_ICONS[gem.name] || "🔹"}</span>
              <span className="gem-name">{gem.name}</span>
              {gem.success_rate > 0 && (
                <span className="gem-stats">{(gem.success_rate * 100).toFixed(0)}%</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-section sidebar-footer">
        <button className="settings-btn" onClick={onOpenSettings}>
          ⚙️ Configuración
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
