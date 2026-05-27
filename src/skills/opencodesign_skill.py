#!/usr/bin/env python3
"""
Open CoDesign Skill - Integrated with Nexus
Provides AI Design capabilities using Open CoDesign
"""
import os
import subprocess
import json
import requests
from pathlib import Path

class OpenCoDesignSkill:
    name = "opencodesign"
    description = "AI Design Tool - Prompt to HTML/React/Slides/PDF"
    
    # Paths
    OPEN_CODESIGN_PATH = r"C:\Program Files\Open CoDesign\Open CoDesign.exe"
    CONFIG_PATH = os.path.expanduser("~/.config/open-codesign/config.toml")
    
    # Available models from config
    MODELS = {
        # Local (Ollama)
        "ollama-qwen": "qwen2.5-coder:7b",
        "ollama-gemma": "gemma2:9b",
        "ollama-deepseek": "deepseek-r1:7b",
        "ollama-llama": "llama3.2:3b",
        "ollama-glm": "glm4:9b",
        # Cloud
        "nexus-core": "qwen2.5-coder",
        "openrouter": "anthropic/claude-3.5-sonnet",
        "groq": "llama-3.3-70b-versatile",
        "google": "gemini-2.5-flash",
    }
    
    def is_installed(self) -> bool:
        return os.path.exists(self.OPEN_CODESIGN_PATH)
    
    def is_running(self) -> bool:
        try:
            r = requests.get("http://localhost:5173", timeout=2)
            return r.status_code == 200
        except:
            return False
    
    def launch(self, model: str = "ollama-qwen") -> dict:
        if not self.is_installed():
            return {"error": "Open CoDesign not installed"}
        
        # Update config to use specified model
        self.set_model(model)
        
        try:
            subprocess.Popen([self.OPEN_CODESIGN_PATH], 
                            cwd=os.path.dirname(self.OPEN_CODESIGN_PATH),
                            creationflags=subprocess.CREATE_NEW_CONSOLE)
            return {"status": "launched", "model": model, "url": "http://localhost:5173"}
        except Exception as e:
            return {"error": str(e)}
    
    def set_model(self, model_id: str) -> bool:
        if model_id not in self.MODELS:
            return False
        
        try:
            # Read config
            config_path = Path(self.CONFIG_PATH).expanduser()
            if config_path.exists():
                content = config_path.read_text()
                content = content.replace(
                    'activeProvider = "ollama-qwen"',
                    f'activeProvider = "{model_id}"'
                )
                content = content.replace(
                    'activeModel = "qwen2.5-coder:7b"',
                    f'activeModel = "{self.MODELS[model_id]}"'
                )
                config_path.write_text(content)
            return True
        except:
            return False
    
    def get_models(self) -> list:
        return list(self.MODELS.keys())
    
    def chat(self, prompt: str, model: str = None) -> dict:
        """Send prompt to Open CoDesign via API if running"""
        if model:
            self.set_model(model)
        
        # Open CoDesign runs on localhost:5173
        # Note: This requires the app to be running with API enabled
        try:
            # This would require enabling API in Open CoDesign
            # For now, just launch with the prompt
            return {
                "status": "redirect",
                "url": f"http://localhost:5173?prompt={requests.utils.quote(prompt)}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "status": "INSTALLED" if self.is_installed() else "NOT_INSTALLED",
            "running": self.is_running(),
            "path": self.OPEN_CODESIGN_PATH,
            "models": self.MODELS,
            "methods": ["is_installed()", "launch(model)", "set_model()", "chat(prompt)"]
        }


def design(prompt: str, model: str = None, launch: bool = True) -> dict:
    """Quick function to use Open CoDesign for design"""
    skill = OpenCoDesignSkill()
    
    if not skill.is_installed():
        return {"error": "Open CoDesign not installed. Install from: https://github.com/OpenCoworkAI/open-codesign"}
    
    if launch:
        return skill.launch(model or "ollama-qwen")
    
    return skill.chat(prompt, model)


# Standalone test
if __name__ == "__main__":
    skill = OpenCoDesignSkill()
    print("=== Open CoDesign Skill ===")
    print(skill.info())