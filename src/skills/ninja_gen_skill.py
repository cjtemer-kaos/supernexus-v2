#!/usr/bin/env python3
"""
NINJA WARS 3 - Image Generation Skill
Integrated with ComfyUI and Locally
"""
import requests
import json
import time
import os
from pathlib import Path

class NinjaWarsGen:
    name = "ninja_gen"
    description = "Generación de imágenes para Ninja Wars 3 vía ComfyUI"
    
    COMFY_URL = "http://localhost:8188"
    OUTPUT_DIR = Path(os.environ.get("COMFYUI_OUTPUT_DIR", str(Path(__file__).resolve().parents[2] / "output" / "comfyui")))
    
    def is_alive(self) -> bool:
        try:
            r = requests.get(f"{self.COMFY_URL}/system_stats", timeout=2)
            return r.status_code == 200
        except:
            return False
    
    def get_models(self) -> list:
        """Lista modelos disponibles"""
        try:
            r = requests.get(f"{self.COMFY_URL}/model_list", timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("checkpoints", [])
            return []
        except:
            return []
    
    def generate(self, prompt: str, negative: str = "", model: str = "Juggernaut-XL_v9.safetensors", 
                width: int = 1024, height: int = 1024, steps: int = 25) -> dict:
        """Genera imagen"""
        if not self.is_alive():
            return {"error": "ComfyUI offline"}
        
        seed = int(time.time()) % 1000000000
        
        workflow = {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": steps, "cfg": 7, "sampler_name": "euler",
                "scheduler": "normal", "denoise": 1, "model": ["4", 0],
                "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]
            }},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "low quality, bad anatomy, blurry", "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "NinjaWars3", "images": ["8", 0]}}
        }
        
        try:
            r = requests.post(f"{self.COMFY_URL}/prompt", json={"prompt": workflow}, timeout=30)
            if r.status_code == 200:
                data = r.json()
                return {"status": "queued", "prompt_id": data.get("prompt_id"), "seed": seed}
            return {"error": r.text}
        except Exception as e:
            return {"error": str(e)}
    
    def wait_for_result(self, prompt_id: str, timeout: int = 180) -> str:
        """Espera resultado"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"{self.COMFY_URL}/history/{prompt_id}", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if "outputs" in data and data["outputs"]:
                        for node_id, output in data["outputs"].items():
                            if "images" in output:
                                return output["images"][0]["filename"]
            except:
                pass
            time.sleep(2)
        return None
    
    # Prompts canon para Ninja Wars 3
    PROMPTS = {
        "ren_base": "RAW PHOTO. 30-year-old rugged Japanese ninja in worn-out OCHRE/TAN shinobi rags. Tattered hood and mask covering face completely. Weathered masculine skin with pores. Dark rocky ancient Japan setting. Cinematic 35mm film grain. NO face visible. NO glowing eyes.",
        
        "ren_mystical": "RAW PHOTO. 30-year-old Japanese ninja (Ren) in indigo ninja attire. Purple storm in background. Orange lotus glowing emblem. Only blue eyes visible through hood. Weathered skin. Volcanic atmosphere. Cinematic. NO face.",
        
        "kaos_base": "RAW PHOTO. 30-year-old Japanese warrior (Kaos) in obsidian samurai armor. Ornate iron Oni mask covering face. Glowing RED eyes piercing through mask. Black katana over shoulder. Dark volcanic forge setting. Ember particles. Chiaroscuro lighting. NO face visible.",
        
        "kaos_mystical": "RAW PHOTO. Kaos, master of war, in black armor with RED EYES GLOWING FROM ONI MASK. Purple mystical energy swirling. Volcanic forge with molten lava. Crimson lotus engravings. Fiery atmosphere. Cinematic dark fantasy."
    }
    
    def info(self) -> dict:
        alive = self.is_alive()
        models = self.get_models() if alive else []
        return {
            "skill": self.name,
            "status": "ONLINE" if alive else "OFFLINE",
            "models": models,
            "prompts": list(self.PROMPTS.keys()),
            "methods": ["is_alive()", "get_models()", "generate(prompt)", "wait_for_result()"]
        }


# Función para usar desde Nexus
def generate_ninja_image(character: str = "ren_base", **kwargs) -> dict:
    """Genera imagen de Ninja Wars"""
    gen = NinjaWarsGen()
    
    if character not in gen.PROMPTS:
        return {"error": f"Character {character} no encontrado. Opciones: {list(gen.PROMPTS.keys())}"}
    
    prompt = gen.PROMPTS[character]
    
    result = gen.generate(prompt, **kwargs)
    return result


if __name__ == "__main__":
    gen = NinjaWarsGen()
    print(gen.info())
    print("\n--- Generando imagen de prueba ---")
    result = gen.generate(gen.PROMPTS["ren_base"])
    print(result)