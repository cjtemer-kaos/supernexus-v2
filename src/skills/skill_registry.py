#!/usr/bin/env python3
# Skill Registry Skill
"""
Auto-detect and index available skills.
"""
import os
import json
import importlib.util

class SkillRegistrySkill:
    def __init__(self):
        self.name = "skill_registry"
        self.description = "Auto-detect available skills"
        self.skills_dir = "skills"
    
    def scan_skills(self, base_path: str = ".") -> dict:
        """Scan and index all available skills"""
        skills_path = os.path.join(base_path, self.skills_dir)
        
        if not os.path.exists(skills_path):
            return {"error": f"Skills directory not found: {skills_path}"}
        
        skills = {
            "python_skills": [],
            "markdown_skills": [],
            "total": 0
        }
        
        # Scan Python files
        for f in os.listdir(skills_path):
            if f.endswith("_skill.py"):
                skill_name = f[:-3]
                skills["python_skills"].append({
                    "name": skill_name,
                    "file": f,
                    "type": "python"
                })
            
            # Scan Markdown files
            elif os.path.isdir(os.path.join(skills_path, f)):
                skill_md = os.path.join(skills_path, f, "SKILL.md")
                if os.path.exists(skill_md):
                    skills["markdown_skills"].append({
                        "name": f,
                        "file": "SKILL.md",
                        "type": "markdown"
                    })
        
        skills["total"] = len(skills["python_skills"]) + len(skills["markdown_skills"])
        
        return skills
    
    def get_skill_info(self, skill_name: str, base_path: str = ".") -> dict:
        """Get detailed info for a specific skill"""
        skills_path = os.path.join(base_path, self.skills_dir)
        
        # Try Python skill
        py_file = os.path.join(skills_path, f"{skill_name}.py")
        if os.path.exists(py_file):
            try:
                spec = importlib.util.spec_from_file_location(skill_name, py_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and attr_name.lower().replace("skill", "") in skill_name.lower():
                        if hasattr(attr, 'info'):
                            return attr.info()
                        return {"name": attr_name, "type": "python"}
            except:
                pass
        
        # Try Markdown skill
        md_file = os.path.join(skills_path, skill_name, "SKILL.md")
        if os.path.exists(md_file):
            with open(md_file, "r") as f:
                content = f.read()
            return {"name": skill_name, "type": "markdown", "file": md_file}
        
        return {"error": f"Skill '{skill_name}' not found"}
    
    def run(self, base_path: str = ".") -> str:
        """Scan and return all skills"""
        return json.dumps(self.scan_skills(base_path), indent=2)
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "methods": ["run(base_path)", "scan_skills(path)", "get_skill_info(name, path)"]
        }

if __name__ == "__main__":
    skill = SkillRegistrySkill()
    print(json.dumps(skill.info(), indent=2))
