"""
NEXUS AUTO-SAVE - Sistema de Persistencia Automática
Guarda contexto y memoria constantemente para mantener estado entre sesiones.
"""

import json
import os
import sys
import time
from datetime import datetime

# ============================================================================
# CONFIGURACION
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTEXT_DIR = os.path.join(BASE_DIR, ".nexus_context")
MEMORY_FILE = os.path.join(CONTEXT_DIR, "memory.json")
CHECKPOINT_FILE = os.path.join(CONTEXT_DIR, "checkpoint.json")
LAST_ACTION_FILE = os.path.join(CONTEXT_DIR, "last_action.log")
SESSION_FILE = os.path.join(CONTEXT_DIR, "session.json")

# Crear directorio
os.makedirs(CONTEXT_DIR, exist_ok=True)

class NexusAutoSaveSkill:
    def __init__(self):
        self.name = "nexus_auto_save"
        self.description = "Sistema de Persistencia Automática y Memoria de Contexto"
        self.load_context()

    def save_context(self, data: dict):
        """Guarda contexto completo del sistema."""
        data["timestamp"] = datetime.now().isoformat()
        data["version"] = "3.5"
        
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return f"[OK] Contexto guardado: {data.get('status', 'unknown')}"

    def load_context(self) -> dict:
        """Carga contexto guardado."""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def checkpoint(self, action: str = "manual", details: str = ""):
        """Guarda checkpoint rápido."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "pid": os.getpid()
        }
        
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        
        # Also log
        with open(LAST_ACTION_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {action}: {details}\n")
        
        return f"[OK] Checkpoint: {action}"

    def get_context_prompt(self) -> str:
        """Generar prompt de contexto para IA."""
        data = self.load_context()
        
        lines = [
            "### NEXUS CONTEXT",
            f"Timestamp: {data.get('timestamp', 'N/A')}",
            f"Status: {data.get('status', 'N/A')}",
        ]
        
        if "active_project" in data:
            lines.append(f"Project: {data['active_project']}")
        
        if "last_task" in data:
            lines.append(f"Last Task: {data['last_task']}")
        
        return "\n".join(lines)

    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "status": self.load_context().get("status", "no_session"),
            "methods": ["save_context(data)", "load_context()", "checkpoint(action, details)", "get_context_prompt()"]
        }

if __name__ == "__main__":
    skill = NexusAutoSaveSkill()
    print(json.dumps(skill.info(), indent=2))