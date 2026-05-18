#!/usr/bin/env python3
# SDD Init Skill
"""
Initialize SDD context in a project, detecting stack and conventions.
"""
import os
import json
import subprocess

class SDDInitSkill:
    def __init__(self):
        self.name = "sdd_init"
        self.description = "Initialize SDD context in project"
    
    def detect_stack(self, project_path: str) -> dict:
        """Detect project stack and conventions"""
        stack = {
            "language": [],
            "framework": [],
            "testing": [],
            "config_files": []
        }
        
        if not os.path.exists(project_path):
            return {"error": "Project path not found"}
        
        # Check files
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'dist', 'build']]
            
            for f in files:
                ext = os.path.splitext(f)[1]
                rel_path = os.path.relpath(os.path.join(root, f), project_path)
                
                # Languages
                if ext == '.py': stack["language"].append("python")
                elif ext in ['.js', '.jsx', '.ts', '.tsx']: stack["language"].append("javascript/typescript")
                elif ext == '.go': stack["language"].append("go")
                elif ext == '.rs': stack["language"].append("rust")
                
                # Frameworks
                if f == 'package.json': 
                    stack["framework"].append("nodejs")
                    with open(os.path.join(root, f)) as pf:
                        pkg = json.load(pf)
                        deps = pkg.get("dependencies", {})
                        if "react" in deps: stack["framework"].append("react")
                        if "next" in deps: stack["framework"].append("nextjs")
                        if "vue" in deps: stack["framework"].append("vue")
                if f == 'requirements.txt': stack["framework"].append("python/pip")
                if f == 'Cargo.toml': stack["framework"].append("rust/cargo")
                if f == 'go.mod': stack["framework"].append("go/modules")
                
                # Testing
                if 'test' in f.lower() or f.startswith('test_') or f.endswith('_test.py'):
                    if 'pytest' in f or 'jest' in f or 'vitest' in f:
                        stack["testing"].append(f)
                
                # Config files
                if f in ['.env', '.env.example', 'docker-compose.yml', 'Dockerfile', 'Makefile', 'tsconfig.json', 'vite.config.js', 'next.config.js']:
                    stack["config_files"].append(rel_path)
        
        # Dedupe
        for k in stack:
            stack[k] = list(set(stack[k]))
        
        return stack
    
    def run(self, project_path: str = ".") -> str:
        """Initialize SDD in project"""
        stack = self.detect_stack(project_path)
        
        result = {
            "skill": "sdd_init",
            "project_path": project_path,
            "detected_stack": stack,
            "status": "ready_for_sdd_explore"
        }
        
        return json.dumps(result, indent=2)
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "methods": ["run(project_path)", "detect_stack(path)"]
        }

if __name__ == "__main__":
    skill = SDDInitSkill()
    print(json.dumps(skill.info(), indent=2))
