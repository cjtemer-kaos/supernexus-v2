#!/usr/bin/env python3
# SDD Design Skill
"""
Technical design with architecture decisions.
"""
import json
import os
from datetime import datetime

class SDDDesignSkill:
    def __init__(self):
        self.name = "sdd_design"
        self.description = "Technical design with architecture decisions"
    
    def generate_design_template(self, change_name: str, spec_ref: str = "") -> dict:
        """Generate design template"""
        return {
            "design": {
                "change_name": change_name,
                "spec_reference": spec_ref,
                "created": datetime.now().isoformat(),
                "architecture": {
                    "overview": "",
                    "components": [],
                    "data_flow": [],
                    "interfaces": []
                },
                "decisions": [
                    {
                        "id": "1",
                        "title": "",
                        "decision": "",
                        "rationale": "",
                        "alternatives_considered": []
                    }
                ],
                "implementation_notes": [],
                "risks": []
            }
        }
    
    def run(self, change_name: str, spec_ref: str = "", output_file: str = "") -> str:
        """Generate technical design"""
        design = self.generate_design_template(change_name, spec_ref)
        
        if output_file:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(design, f, indent=2)
            return f"[OK] Design saved to {output_file}"
        
        return json.dumps(design, indent=2)
    
    def add_decision(self, design: dict, title: str, decision: str, rationale: str) -> dict:
        """Add architecture decision to design"""
        if "design" not in design or "decisions" not in design["design"]:
            return design
        
        new_decision = {
            "id": str(len(design["design"]["decisions"]) + 1),
            "title": title,
            "decision": decision,
            "rationale": rationale,
            "alternatives_considered": []
        }
        design["design"]["decisions"].append(new_decision)
        return design
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "methods": ["run(change_name, spec_ref, output_file)", "add_decision(design, title, decision, rationale)"]
        }

if __name__ == "__main__":
    skill = SDDDesignSkill()
    print(json.dumps(skill.info(), indent=2))
