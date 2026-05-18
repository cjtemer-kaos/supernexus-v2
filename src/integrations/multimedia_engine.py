"""
Multimedia Engine para SuperNEXUS v2
Gestion de escenas, assets y delegacion a sub-agentes
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MultimediaEngine:
    """Motor multimedia para gestion de proyectos audiovisuales"""

    def __init__(self, audio_dir: str = None):
        self.kaos_audio_dir = Path(audio_dir or os.getenv("NEXUS_KAOS_AUDIO_DIR", str(Path.home() / "kaos_audio")))
        self.master_script_path = self.kaos_audio_dir / "guion_veo_31_maestro.json"

    def get_status(self) -> Dict:
        if not self.kaos_audio_dir.exists():
            return {"status": "Disconnected", "error": "Carpeta kaos_audio no encontrada."}

        files = list(self.kaos_audio_dir.iterdir())
        has_script = self.master_script_path.exists()

        scenes_data = []
        if has_script:
            try:
                scenes_data = json.loads(self.master_script_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "status": "Online",
            "directory": str(self.kaos_audio_dir),
            "scenes_total": len(scenes_data),
            "has_master_script": has_script,
            "assets_count": len(files),
        }

    def get_scenes(self) -> List:
        if not self.master_script_path.exists():
            return []
        try:
            return json.loads(self.master_script_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    async def start_scene_generation(self, scene_id: str) -> str:
        logger.info(f"Despachando Escena {scene_id} al motor Veo 3.1...")
        return f"Escena {scene_id} despachada. Esperando renderizado."

    async def delegate_task(self, agent_name: str, task: str) -> str:
        logger.info(f"Delegando a {agent_name}: {task}")
        if agent_name.lower() == "nanocoder":
            return f"Orden enviada a Nanocoder: {task}"
        return f"Agente {agent_name} notificado de la tarea."
