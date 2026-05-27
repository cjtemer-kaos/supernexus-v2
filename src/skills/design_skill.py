#!/usr/bin/env python3
"""
NEXUS DESIGN SKILL - Generación de UI con IA
Basado en video: "Mejora el UI de tus Aplicaciones Web con IA"

Métodos:
1. PureCode AI - Generar UI desde prompts
2. Gemini - Generar código Tailwind/React
3. Cursor - Ajustes precisos con Stage Wise
4. Browser MCP - Clonar diseños existentes

Tokens de diseño:
- --bg-void: #050508
- --cyan: #00f5ff
- --magenta: #ff00aa
"""
import os
import json
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

class NexusDesignSkill:
    def __init__(self):
        self.name = "design"
        self.description = "Generación y mejora de UI con IA"
        self.tokens = {
            "--bg-void": "#050508",
            "--bg-obsidian": "#0a0a0f",
            "--cyan": "#00f5ff",
            "--magenta": "#ff00aa",
            "--text-primary": "#e8e8e8",
            "--text-muted": "#888899"
        }
        self.skills_path = str(Path(__file__).parent / "hub")
        
    def generate_with_gemini(self, prompt, framework="tailwind"):
        """Genera UI usando Gemini
        
        Args:
            prompt: Descripción del componente UI
            framework: "tailwind" | "react" | "bootstrap"
        """
        full_prompt = f"""Genera código {framework} para el siguiente componente UI.

Requisitos:
- Tema: Deep Space Black con acentos Cyan (#00f5ff) y Magenta (#ff00aa)
- Fondo principal: #050508
- Texto: #e8e8e8
- Responsive: móvil, tablet, desktop

Componente: {prompt}

Salida (3 bloques):
1. Datos de ejemplo (JSON mock data)
2. Componente {framework.upper()}
3. Instrucciones de setup si es necesario
"""
        return self._call_gemini(full_prompt)
    
    def generate_modern_card(self, title, description, image_url=None, tags=None):
        """Genera una card moderna"""
        prompt = f"""Card moderna con:
- Título: {title}
- Descripción: {description}
- Imagen: {image_url or 'placeholder'}
- Tags: {tags or []}
- Estilo: glassmorphism con border cyan
- Hover: glow effect
"""
        return self.generate_with_gemini(prompt, "tailwind")
    
    def generate_dashboard_layout(self, components):
        """Genera layout de dashboard
        
        Args:
            components: lista de componentes ['charts', 'tables', 'stats', 'sidebar']
        """
        prompt = f"""Dashboard layout con:
- Sidebar fijo a la izquierda
- Header con búsqueda y perfil
- Área principal con grid de {len(components)} items
- Componentes: {', '.join(components)}
- Tema: Dark mode Neural
"""
        return self.generate_with_gemini(prompt, "react")
    
    def clone_design(self, url):
        """Clona diseño existente usando Browser MCP
        
        Args:
            url: URL del sitio a clonar
        """
        return {
            "status": "ready",
            "method": "browser_mcp",
            "command": f"/clone-site {url}",
            "note": "Ejecutar en Cursor con Browser MCP"
        }
    
    def analyze_design(self, url):
        """Analiza un diseño existente"""
        prompt = f"""Analiza el diseño de esta web: {url}

Proporciona:
1. Paleta de colores
2. Tipografía
3. Componentes principales
4. Layout structure
5. Mejoras potenciales
"""
        return self._call_gemini(prompt)
    
    def _call_gemini(self, prompt):
        """Llama a Gemini para generar código"""
        # Por ahora retorna estructura vacía - completar con API key
        return {
            "status": "template_ready",
            "prompt": prompt,
            "note": "Implementar con gemini_skill.py"
        }
    
    def create_purecode_prompt(self, component):
        """Genera prompt para PureCode AI"""
        base = f"""Crea un componente {component} para una app de IA.

Requisitos obligatorios:
- Tema: Deep Space Black (bg #050508)
- Acento primario: Cyan (#00f5ff)
- Acento secundario: Magenta (#ff00aa)
- Estilo: Moderno, futurista, glassmorphism
- Framework: React + TailwindCSS
- Responsive: Sí

Incluye:
- Animaciones suaves
- Hover states
- Transiciones
- Bordes sutiles con glow
"""
        return {"prompt": base, "tool": "purecode.ai"}
    
    def create_cursor_prompt(self, component):
        """Genera prompt estructurado para Cursor IDE"""
        prompt = f"""Crea el componente "{component}" siguiendo esta especificación:

#UI SPEC
- Nombre: {component}
- Tipo: Componente React
- Props: title, description, onAction
- Estados: default, hover, active, disabled
- Responsive: mobile-first

#STYLE
- Theme: Nexus Neural Design
- Background: #050508
- Primary: #00f5ff
- Secondary: #ff00aa
- Fonts: Inter, JetBrains Mono
- Effects: glow, glassmorphism

#LAYOUT
- Mobile: stack vertical
- Tablet: 2 columns
- Desktop: responsive grid

#BEHAVIOR
- hover: scale(1.02) + glow
- click: ripple effect
- transition: 200ms ease

Genera el código completo."""
        return {"prompt": prompt, "tool": "cursor"}
    
    def apply_tweak(self, element, change):
        """Aplica tweak específico usando Stage Wise
        
        Args:
            element: Elemento a modificar
            change: Cambio necesario
        """
        return {
            "method": "stage_wise",
            "action": f"Seleccionar {element}",
            "instruction": change,
            "note": "Usar Stage Wise en Cursor para ajustes precisos"
        }
    
    def optimize_for_nexus(self, code, style="glass"):
        """Optimiza código para el tema Nexus
        
        Args:
            code: Código CSS/Tailwind existente
            style: "glass" | "solid" | "neon"
        """
        styles = {
            "glass": {
                "background": "rgba(5, 5, 8, 0.8)",
                "backdrop_filter": "blur(10px)",
                "border": "1px solid rgba(0, 245, 255, 0.2)",
            },
            "solid": {
                "background": "#0a0a0f",
                "border": "1px solid #00f5ff",
            },
            "neon": {
                "background": "#050508",
                "box_shadow": "0 0 20px rgba(0, 245, 255, 0.5)",
            }
        }
        return {
            "original": code,
            "nexus_style": styles.get(style, styles["glass"]),
            "applied": True
        }
    
    def export_tokens(self):
        """Exporta tokens de diseño para usar en otros proyectos"""
        return {
            "name": "nexus-neural",
            "tokens": self.tokens,
            "usage": "CSS variables o Tailwind config"
        }
    
    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "methods": [
                "generate_with_gemini",
                "generate_modern_card",
                "generate_dashboard_layout",
                "clone_design",
                "analyze_design",
                "create_purecode_prompt",
                "create_cursor_prompt",
                "apply_tweak",
                "optimize_for_nexus",
                "export_tokens"
            ],
            "tokens": self.tokens
        }

if __name__ == "__main__":
    skill = NexusDesignSkill()
    print(json.dumps(skill.info(), indent=2))