#!/usr/bin/env python3
"""
SDD Skill - Spec-Driven Development
Implementa el flujo Explore -> Propose -> Apply -> Verify -> Archive
"""

import os
import json
from pathlib import Path
from datetime import datetime

class SDDSkill:
    def __init__(self):
        self.name = "sdd"
        self.description = "Spec-Driven Development Flow (Explore, Propose, Apply, Verify, Archive)"
        self.base_dir = Path("memory/sdd_sessions")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def init_session(self, project_name: str):
        """Inicia una nueva sesión de SDD para un proyecto."""
        session_id = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        
        state = {
            "project": project_name,
            "session_id": session_id,
            "current_phase": "init",
            "phases": {
                "explore": {"status": "pending", "findings": []},
                "propose": {"status": "pending", "proposal": ""},
                "apply": {"status": "pending", "tasks": []},
                "verify": {"status": "pending", "results": []},
                "archive": {"status": "pending"}
            }
        }
        self._save_state(session_id, state)
        return {"session_id": session_id, "message": f"Sesión SDD iniciada para {project_name}"}

    def update_phase(self, session_id: str, phase: str, content: dict):
        """Actualiza el contenido de una fase específica."""
        state = self._load_state(session_id)
        if not state:
            return {"error": "Sesión no encontrada"}
        
        if phase not in state["phases"]:
            return {"error": f"Fase {phase} no válida"}
            
        state["phases"][phase].update(content)
        state["phases"][phase]["status"] = "completed"
        state["current_phase"] = phase
        self._save_state(session_id, state)
        return {"session_id": session_id, "phase": phase, "status": "updated"}

    def get_status(self, session_id: str):
        """Obtiene el estado actual de la sesión."""
        return self._load_state(session_id)

    def _save_state(self, session_id, state):
        path = self.base_dir / session_id / "state.json"
        with open(path, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self, session_id):
        path = self.base_dir / session_id / "state.json"
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
        return None

    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "phases": ["explore", "propose", "apply", "verify", "archive"],
            "methods": ["init_session(project)", "update_phase(id, phase, content)", "get_status(id)"]
        }

if __name__ == "__main__":
    skill = SDDSkill()
    print(json.dumps(skill.info(), indent=2))
