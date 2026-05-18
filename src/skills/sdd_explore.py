#!/usr/bin/env python3
# SDD Explore Skill
"""
Investigates codebase before committing to a change.
"""
import os
import json

class SDDExplore:
    def __init__(self):
        self.name = "sdd-explore"
        self.description = "Investigate codebase before change"
    
    def run(self, project_path: str, topic: str = "") -> dict:
        """Explore codebase"""
        results = {
            "phase": "explore",
            "project": project_path,
            "topic": topic,
            "structure": [],
            "findings": [],
            "risks": []
        }
        
        # Scan structure
        if os.path.exists(project_path):
            for root, dirs, files in os.walk(project_path):
                # Skip hidden and cache
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                for f in files:
                    if f.endswith(('.py', '.md', '.json', '.yaml', '.yml')):
                        results["structure"].append(os.path.relpath(os.path.join(root, f), project_path))
        
        return results
    
    def info(self) -> dict:
        return {"name": self.name, "description": self.description}

if __name__ == "__main__":
    skill = SDDExplore()
    print(json.dumps(skill.info(), indent=2))