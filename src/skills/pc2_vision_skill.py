# NEXUS Remote Node VISION - Visual Monitoring Skill
"""
Skill para vigilancia visual en tiempo real de Remote Node vía capturadora USB.
Permite al Director "ver" qué ocurre en el nodo remoto.
"""

import subprocess
import os
from typing import Dict

class Remote NodeVisionSkill:
    def __init__(self):
        self.name = "Remote NodeVision"
        self.device = "USB Video"
        self.output_path = os.getenv("NEXUS_VISION_OUTPUT", str(Path.home() / "nexus_vision.png"))

    def info(self) -> Dict:
        return {
            "name": self.name,
            "device": self.device,
            "methods": ["capture_screen", "analyze_screen"]
        }

    def capture_screen(self) -> str:
        """Captura un frame actual del escritorio de Remote Node."""
        cmd = f'ffmpeg -f dshow -i video="{self.device}" -frames:v 1 -y "{self.output_path}"'
        try:
            # Ejecutar de forma silenciosa
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Captura realizada con éxito en {self.output_path}"
        except Exception as e:
            return f"Error en captura visual: {e}"

    def analyze_screen(self) -> str:
        """Captura y analiza el contenido visual de Remote Node usando el modelo de visión local."""
        self.capture_screen()
        # Aquí se integraría con el router para pasar la imagen a Llava
        return f"Imagen de Remote Node capturada. Listo para análisis visual en {self.output_path}."

# Instancia para el manager
Remote Node_vision = Remote NodeVisionSkill()
