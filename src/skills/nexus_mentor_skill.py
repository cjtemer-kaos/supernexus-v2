#!/usr/bin/env python3
"""
Nexus Mentor Skill - Canalización de Mentores
Permite a Nexus adoptar el estilo y conocimiento de mentores registrados.
"""

import json
from pathlib import Path

MENTORS_FILE = Path(__file__).parent.parent.parent / "brain" / "1_NEXUS" / "MENTORS.md"

class NexusMentorSkill:
    def __init__(self):
        self.name = "nexus_mentor"
        self.description = "Canaliza el conocimiento y estilo de mentores de la biblioteca Nexus"
        self.active_mentor = None

    def get_mentor_prompt(self, mentor_name: str = None):
        """Genera un prompt basado en el mentor seleccionado."""
        # Por ahora simulamos la selección, en el futuro leeremos MENTORS.md dinámicamente
        mentors = {
            "schurmann": {
                "name": "Nicolás Schürmann (Hola Mundo)",
                "style": "Didáctico, enfocado en arquitectura limpia, carrera profesional y pragmatismo.",
                "traits": ["arquitectura", "clean code", "seniority"]
            },
            "primeagen": {
                "name": "The Primeagen",
                "style": "Extremadamente técnico, enfocado en performance, Rust, Vim y eficiencia pura.",
                "traits": ["performance", "rust", "low-level"]
            },
            "fireship": {
                "name": "Fireship",
                "style": "Rápido, conciso, enfocado en las últimas tendencias tecnológicas y brevedad extrema.",
                "traits": ["speed", "modern-stack", "concise"]
            }
        }
        
        mentor = mentors.get(mentor_name.lower()) if mentor_name else None
        if not mentor:
            return "Eres el Sabio de Nexus, un orquestador de conocimiento general."
            
        return (
            f"Estás canalizando a {mentor['name']}. "
            f"Tu estilo es: {mentor['style']} "
            f"Tus prioridades actuales son: {', '.join(mentor['traits'])}."
        )

    def list_mentors(self):
        return ["schurmann", "primeagen", "fireship"]

    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "available_mentors": self.list_mentors()
        }

if __name__ == "__main__":
    skill = NexusMentorSkill()
    print(json.dumps(skill.info(), indent=2))
