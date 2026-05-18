#!/usr/bin/env python3
"""Nexus Brain Sync - Sincroniza el cerebro entre nodos"""
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

class NexusBrainSync:
    def __init__(self):
        self.name = "brain_sync"
        self.brain_path = os.getenv("NEXUS_BRAIN_PATH", str(Path(__file__).parent.parent.parent / "brain"))
        self.remote_path = os.getenv("NEXUS_REMOTE_BRAIN", "")
        self.remote_available = bool(self.remote_path and os.path.exists(self.remote_path))

    def info(self):
        return {
            "skill": self.name,
            "description": "Sincroniza cerebro Nexus entre sistemas",
            "brain_path": self.brain_path,
            "remote_available": self.remote_available
        }

    def sync_to_remote(self):
        """Sincroniza brain al nodo remoto"""
        if not self.remote_available:
            return {"error": "Remote brain not available. Set NEXUS_REMOTE_BRAIN env var."}

        result = subprocess.run(
            ["rsync", "-av", "--delete", self.brain_path + "/", self.remote_path + "/"],
            capture_output=True, text=True
        )
        return {"sync": "local → remote", "result": result.returncode == 0, "output": result.stdout[:500]}

    def sync_from_remote(self):
        """Sincroniza brain del nodo remoto"""
        if not self.remote_available:
            return {"error": "Remote brain not available"}

        result = subprocess.run(
            ["rsync", "-av", "--delete", self.remote_path + "/", self.brain_path + "/"],
            capture_output=True, text=True
        )
        return {"sync": "remote → local", "result": result.returncode == 0, "output": result.stdout[:500]}

    def status(self):
        """Estado del cerebro"""
        files = []
        if os.path.exists(self.brain_path):
            for root, dirs, filenames in os.walk(self.brain_path):
                files = [f for f in filenames if f.endswith(".md")]
        return {
            "brain_path": self.brain_path,
            "files": files[:10],
            "remote_available": self.remote_available
        }
    
    def add_link(self, link_type, title, url, description="", relevance="Media"):
        """Agregar link al brain"""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        if link_type == "estudio":
            file_path = os.path.join(self.brain_path, "1_NEXUS", "STUDY_LINKS.md")
        elif link_type == "repo":
            file_path = os.path.join(self.brain_path, "1_NEXUS", "REPOSITORIES.md")
        elif link_type == "tool":
            file_path = os.path.join(self.brain_path, "2_HABILIDADES", "TOOLS_COLLECTION.md")
        else:
            file_path = os.path.join(self.brain_path, "1_NEXUS", "LINKS_ARCHIVE.md")
        
        entry = f"""
### {timestamp} - {link_type.upper()}
- **Título**: {title}
- **URL**: {url}
- **Descripción**: {description}
- **Relevancia**: {relevancia}
"""
        
        with open(file_path, "a") as f:
            f.write(entry)
        
        return {"added": title, "type": link_type, "file": file_path}

if __name__ == "__main__":
    skill = NexusBrainSync()
    print(json.dumps(skill.info(), indent=2))