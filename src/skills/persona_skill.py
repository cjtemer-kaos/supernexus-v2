#!/usr/bin/env python3
"""
NEXUS Persona Skill
Maneja las múltiples personalidades del Director
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import os
import json
from pathlib import Path
from typing import Dict, Optional, List

IAS_ROOT = Path(os.getenv("NEXUS_HOME", Path.home() / ".nexus"))

PERSONALITIES = {
    "director": {
        "name": "Nexus Director",
        "description": "El líder supremo de Nexus. Directo, conciso, ejecutivo.",
        "voice": {"speed": 1.0, "tone": "formal", "pitch": 0},
        "color": "#00ff88",
        "emoji": "🎭",
        "temperature": 0.7,
        "tags": ["lider", "ejecutivo"]
    },
    "ejecutivo": {
        "name": "Ejecutivo",
        "description": "Especialista en tareas administrativas y de gestión.",
        "voice": {"speed": 1.1, "tone": "intense", "pitch": 2},
        "color": "#ff4444",
        "emoji": "⚔️",
        "temperature": 0.8,
        "tags": ["action", "management", "building"]
    },
    "creativo": {
        "name": "Musa",
        "description": "Creador artístico y diseñador visual.",
        "voice": {"speed": 0.9, "tone": "artistic", "pitch": -1},
        "color": "#ff66ff",
        "emoji": "🎨",
        "temperature": 0.9,
        "tags": ["art", "design", "music"]
    },
    "sabio": {
        "name": "Scholar",
        "description": "Mentor y especialista en investigación.",
        "voice": {"speed": 0.8, "tone": "calm", "pitch": -2},
        "color": "#4488ff",
        "emoji": "📚",
        "temperature": 0.5,
        "tags": ["analysis", "research", "mentor"]
    },
    "arquitecto": {
        "name": "Architect",
        "description": "Diseñador de sistemas y estructuras.",
        "voice": {"speed": 1.0, "tone": "technical", "pitch": 0},
        "color": "#44ffaa",
        "emoji": "🏗️",
        "temperature": 0.6,
        "tags": ["systems", "architecture", "design"]
    },
    "codificador": {
        "name": "Codex",
        "description": "Desarrollador y experto en código.",
        "voice": {"speed": 1.2, "tone": "technical", "pitch": 1},
        "color": "#00ff00",
        "emoji": "💻",
        "temperature": 0.4,
        "tags": ["code", "development", "debug"]
    }
}


class PersonaSkill:
    def __init__(self):
        self.name = "Persona"
        self.version = "1.0"
        self.current = "director"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        config_path = IAS_ROOT / "memory" / "persona_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return {"current": "director", "personalities": list(PERSONALITIES.keys())}
    
    def set_mode(self, mode: str) -> bool:
        """Cambia la personalidad"""
        if mode not in PERSONALITIES:
            return False
        self.current = mode
        config_path = IAS_ROOT / "memory" / "persona_config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"current": mode}, f)
        except:
            pass
        return True
    
    def prompt_for(self) -> str:
        """Genera prompt de la personalidad actual"""
        if self.current not in PERSONALITIES:
            self.current = "director"
        
        p = PERSONALITIES[self.current]
        return f"""### CURRENT PERSONA ###
Eres {p['name']}.
{p['description']}
Color: {p['color']} | Emoji: {p['emoji']}
Tags: {', '.join(p['tags'])}"""
    
    def list_modes(self) -> List[str]:
        """Lista personalidades disponibles"""
        return list(PERSONALITIES.keys())
    
    def get_current_mode(self) -> str:
        """Retorna personalidad actual"""
        return self.current
    
    def get_info(self) -> Dict:
        """Info de la personality actual"""
        return PERSONALITIES.get(self.current, PERSONALITIES["director"])


persona_skill = PersonaSkill()