#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spline Skill - 3D web elements
Uso: Generar escenas 3D interactivas con Spline
"""
import json
import urllib.request
import urllib.error

class SplineSkill:
    def __init__(self):
        self.name = "SplineSkill"
        self.api_base = "https://api.spline.design"
    
    def generate_embed(self, scene_url: str, height: str = "500px") -> str:
        """Genera iframe para embeber escena de Spline"""
        code = f"""<iframe 
  src="{scene_url}" 
  width="100%" 
  height="{height}"
  frameborder="0" 
  webkitallowfullscreen 
  mozallowfullscreen 
  allowfullscreen
></iframe>"""
        return f"[CODE]\n{code}"
    
    def generate_react_component(self, scene_url: str) -> str:
        """Genera componente React para Spline"""
        code = f"""import Spline from '@splinetool/react-spline';

export default function Scene() {{
  return (
    <Spline 
      scene="{scene_url}" 
      onLoad={{(spline) => console.log('Spline loaded', spline)}}
      onMouseDown={{(e) => console.log('Mouse down', e)}}
    />
  );
}}
"""
        return f"[CODE]\n{code}"
    
    def install_react(self) -> str:
        """Comando para instalar Spline para React"""
        return "npm install @splinetool/react-spline"
    
    def generate_basic_scene(self, elements: list = None) -> dict:
        """Genera estructura básica de escena Spline (JSON)"""
        if elements is None:
            elements = ["cube", "sphere", "light"]
        
        scene = {
            "name": "NEXUS Scene",
            "elements": []
        }
        
        for i, elem in enumerate(elements):
            scene["elements"].append({
                "type": elem,
                "position": [i * 2, 0, 0],
                "scale": [1, 1, 1],
                "rotation": [0, 0, 0]
            })
        
        return scene
    
    def generate_animation_js(self, element_id: str, animation_type: str = "rotate") -> str:
        """Genera código JS para animar elementos Spline"""
        animations = {
            "rotate": f"""const elem = document.getElementById('{element_id}');
setInterval(() => {{
  const current = elem.rotation.y;
  elem.rotation.y = current + 0.01;
}}, 16);""",
            "bounce": f"""const elem = document.getElementById('{element_id}');
let y = 0, dir = 1;
setInterval(() => {{
  y += dir * 0.02;
  if (y > 2) dir = -1;
  if (y < 0) dir = 1;
  elem.position.y = y;
}}, 16);""",
            "pulse": f"""const elem = document.getElementById('{element_id}');
let scale = 1, dir = 1;
setInterval(() => {{
  scale += dir * 0.01;
  if (scale > 1.5) dir = -1;
  if (scale < 0.5) dir = 1;
  elem.scale.set(scale, scale, scale);
}}, 16);"""
        }
        
        return f"[CODE]\n{animations.get(animation_type, animations['rotate'])}"
    
    def spline_vs_threejs(self) -> str:
        """Comparación entre Spline y Three.js"""
        return """Spline vs Three.js:

Spline:
+ Visual editor (no-code)
+ Rápido para prototipos
+ Integración fácil via iframe
- Menos control fino
- Requiere editor de Spline

Three.js:
+ Control total de la escena
+ Más flexible
- Curva de aprendizaje alta
- Código más complejo

Recomendación: Usa Spline para prototipos rápidos, Three.js para producción compleja.
"""
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": "3D web elements interactivos",
            "install_react": self.install_react(),
            "docs": "https://docs.spline.design",
            "editor": "https://spline.design"
        }

if __name__ == "__main__":
    skill = SplineSkill()
    print(json.dumps(skill.info(), indent=2))
