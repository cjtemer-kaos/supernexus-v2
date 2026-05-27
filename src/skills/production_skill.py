import os
import re
import time
import sys
from pathlib import Path

# Intentar importar la skill base de ComfyUI
sys.path.append(os.path.dirname(__file__))
try:
    from comfy_skill import ComfyUISkill
except ImportError:
    ComfyUISkill = None

class ProductionSkill:
    def __init__(self):
        self.name = "nexus_production"
        self.description = "Habilidad de orquestación de producción masiva para cine y fotografía documental IA."
        self.comfy = ComfyUISkill() if ComfyUISkill else None

    def parse_markdown_script(self, file_path: str) -> list:
        """Extrae escenas y prompts de un archivo Markdown."""
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Patrón estándar de guion técnico Nexus: ### Escena X: [Nombre] ... **Prompt:** "[Prompt]"
        scenes = re.findall(r'### (Escena \d+:.*?)\n.*?\*\*Prompt:\*\* "(.*?)"', content, re.DOTALL)
        return scenes

    def run_batch_production(self, script_path: str, model: str = "RealVisXL_V5.safetensors", steps: int = 40) -> dict:
        """Ejecuta toda la producción de un guion técnico."""
        if not self.comfy:
            return {"error": "ComfyUISkill no disponible."}
        
        scenes = self.parse_markdown_script(script_path)
        if not scenes:
            return {"error": f"No se encontraron escenas en {script_path}"}
        
        results = []
        for name, prompt in scenes:
            res = self.comfy.execute(prompt_text=prompt, model=model, steps=steps)
            results.append({"scene": name, "response": res})
            time.sleep(1) # Delay de seguridad
            
        return {"status": "batch_initiated", "total_scenes": len(scenes), "details": results}

    def generate_fidelity_portrait(self, character_desc: str, context: str = "damp bamboo forest, misty dawn") -> str:
        """Genera un retrato de alta fidelidad basado en el estándar Pai."""
        if not self.comfy:
            return "Error: ComfyUI no disponible."
            
        pai_prompt = f"RAW full-frame historical photo, 17th century. {character_desc}. {context}. Natural lighting, shot on 35mm film, slight grain, muted natural colors, extreme detail on textures. Historically accurate reconstruction."
        
        return self.comfy.execute(prompt_text=pai_prompt)

    def info(self) -> dict:
        return {
            "skill": self.name,
            "methods": ["parse_markdown_script(path)", "run_batch_production(path, model, steps)", "generate_fidelity_portrait(desc, context)"],
            "comfy_status": "READY" if self.comfy else "MISSING"
        }

def get_skill():
    return ProductionSkill()
