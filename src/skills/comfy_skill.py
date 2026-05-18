import requests
import json
import os
import subprocess
import time
import sys

class ComfyUISkill:
    """
    NEXUS COMFYUI MASTERCLASS UPGRADE (v2.0)
    Integración soberana con descubrimiento automático y soporte para Flux/LTX.
    """
    def __init__(self, api_url="http://127.0.0.1:8188"):
        self.name = "comfyui"
        self.api_url = api_url
        self.install_path = os.getenv("NEXUS_COMFYUI_PATH", str(Path.home() / "ComfyUI"))
        self.last_history_id = None

    def is_alive(self) -> bool:
        try:
            response = requests.get(f"{self.api_url}/system_stats", timeout=2)
            return response.status_code == 200
        except:
            return False

    def discover_nodes(self):
        """Descubrimiento agnóstico de nodos instalados (Masterclass Rule)."""
        if not self.is_alive(): return {"error": "Server offline"}
        try:
            response = requests.get(f"{self.api_url}/object_info", timeout=5)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def get_models(self):
        """Lista modelos disponibles en el servidor."""
        if not self.is_alive(): return []
        try:
            # Intentamos obtener modelos vía object_info del nodo CheckpointLoaderSimple
            info = self.discover_nodes()
            return info.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        except:
            return []

    def build_flux_workflow(self, prompt, model="flux1-dev.safetensors", width=1024, height=1024):
        """Workflow optimizado para Flux (NVIDIA/RunPod Guide)."""
        # Estructura simplificada para demostración, escalable a nodos personalizados
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": int(time.time()), "steps": 25, "cfg": 1,
                    "sampler_name": "euler", "scheduler": "simple", "denoise": 1,
                    "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]
                }
            },
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["4", 1]}}, # Flux prefiere prompts positivos
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "NEXUS_FLUX", "images": ["8", 0]}}
        }

    def execute_batch(self, prompts, model="RealVisXL_V5.safetensors"):
        """Ejecución por lotes (x10 Productivity)."""
        results = []
        for p in prompts:
            res = self.execute(p, model=model)
            results.append(res)
            time.sleep(1) # Pequeño delay para el encolador
        return results

    def execute(self, prompt_text: str, **kwargs):
        """Ejecución base compatible con API."""
        if not self.is_alive(): return "OFFLINE"
        
        workflow = kwargs.get("workflow")
        if not workflow:
            # Por defecto usa SDXL o el especificado
            model = kwargs.get("model", "RealVisXL_V5.safetensors")
            workflow = self.build_flux_workflow(prompt_text, model=model) if "flux" in model.lower() else self._standard_workflow(prompt_text, **kwargs)

        try:
            response = requests.post(f"{self.api_url}/prompt", json={"prompt": workflow}, timeout=10)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _standard_workflow(self, prompt, **kwargs):
        # ... (Mantener lógica anterior mejorada)
        model = kwargs.get("model", "RealVisXL_V5.safetensors")
        return {
            "3": {"class_type": "KSampler", "inputs": {"seed": int(time.time()), "steps": 30, "cfg": 7, "sampler_name": "dpmpp_2m", "scheduler": "karras", "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "low quality, bad anatomy", "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "NEXUS_STD", "images": ["8", 0]}}
        }

if __name__ == "__main__":
    comfy = ComfyUISkill()
    if comfy.is_alive():
        print("[NEXUS] Modelos detectados:", comfy.get_models()[:5])
    else:
        print("[NEXUS] ComfyUI Offline")
