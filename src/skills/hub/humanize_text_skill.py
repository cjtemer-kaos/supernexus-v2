# NEXUS WRITEGEM - Humanize AI Text Skill
"""
Skill para humanizar texto generado por IA
Autor: Nexus AI
Fecha: 2026-04-29
Origen: ClawHub - Humanize AI text (8,771+ downloads)
"""

import re
from typing import Dict, List

class HumanizeTextSkill:
    """
    Hace que texto generado por IA suene más natural y humano
    Perfecto para WriteGem - escritura natural
    """
    
    def __init__(self):
        self.name = "Humanize AI Text"
        self.version = "1.0"
        
        self.ai_patterns = [
            r"\b(es importante destacar|también conocido como|en conclusión)\b",
            r"\b(mediante el uso de|con el objetivo de|para lograr)\b",
            r"\b(se puede observar que|es necesario mencionar)\b",
            r"\b(En primer lugar|En segundo lugar|Por último)\b",
            r"\b(cabe destacar|sin lugar a dudas|indudablemente)\b"
        ]
        
        self.human_equivalents = {
            "es importante destacar": "mira",
            "también conocido como": "es decir",
            "en conclusión": "al final",
            "mediante el uso de": "usando",
            "con el objetivo de": "para",
            "para lograr": "y conseguir",
            "se puede observar que": "ves que",
            "es necesario mencionar": "debemos decir",
            "En primer lugar": "Primero",
            "En segundo lugar": "Segundo",
            "Por último": "Finalmente",
            "cabe destacar": "fíjate",
            "sin lugar a dudas": "claro",
            "indudablemente": "sin duda"
        }
    
    def humanize(self, text: str, intensity: str = "medium") -> str:
        """Convierte texto IA en texto natural"""
        result = text
        
        for pattern, replacement in self.human_equivalents.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Reducir puntuación excesiva
        result = re.sub(r'\.{2,}', '.', result)
        result = re.sub(r'\!{2,}', '!', result)
        result = re.sub(r'\?{2,}', '?', result)
        
        # Agregar variaciones naturales
        if intensity == "high":
            result = result.replace(".", ". ").replace("!", "!")
            
        return result
    
    def check_ai_score(self, text: str) -> Dict:
        """Detecta cuánto parece texto de IA"""
        ai_markers = 0
        for pattern in self.ai_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                ai_markers += 1
        
        score = min(100, ai_markers * 20)
        
        return {
            "ai_score": score,
            "is_ai_like": score > 50,
            "suggestions": [
                "Usar frases más cortas",
                "Eliminar muletillas formales",
                "Agregar ejemplos personales"
            ] if score > 30 else []
        }
    
    def make_conversational(self, text: str) -> str:
        """Convierte a estilo conversacional"""
        result = text
        result = result.replace("usted", "vos")
        result = result.replace("Usted", "Vos")
        result = result.replace("para usted", "para vos")
        return result

humanize_skill = HumanizeTextSkill()