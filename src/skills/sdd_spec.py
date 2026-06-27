#!/usr/bin/env python3
# SDD Spec Skill
"""
Write specifications with requirements and scenarios.
"""
import json
import os
from datetime import datetime

class SDDSpecSkill:
    def __init__(self):
        self.name = "sdd_spec"
        self.description = "Write specifications with requirements"
    
    def generate_spec_template(self, change_name: str, description: str = "") -> dict:
        """Generate specification template"""
        return {
            "spec": {
                "change_name": change_name,
                "description": description,
                "created": datetime.now().isoformat(),
                "requirements": {
                    "functional": [],
                    "non_functional": [],
                    "constraints": []
                },
                "scenarios": [
                    {
                        "id": "1",
                        "name": "Happy path",
                        "description": "Principal workflow",
                        "steps": [],
                        "expected_result": ""
                    }
                ],
                "acceptance_criteria": [],
                "edge_cases": []
            }
        }
    
    def run(self, change_name: str, description: str = "", output_file: str = "") -> str:
        """Generate specification"""
        spec = self.generate_spec_template(change_name, description)
        
        if output_file:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(spec, f, indent=2)
            return f"[OK] Spec saved to {output_file}"
        
        return json.dumps(spec, indent=2)
    
    def validate_spec(self, spec_data: dict) -> dict:
        """Validate a spec has required fields"""
        required = ["change_name", "requirements", "scenarios", "acceptance_criteria"]
        missing = [f for f in required if f not in spec_data]
        
        return {
            "valid": len(missing) == 0,
            "missing_fields": missing,
            "score": f"{len(required) - len(missing)}/{len(required)}"
        }
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "methods": ["run(change_name, description, output_file)", "validate_spec(data)"]
        }

if __name__ == "__main__":
    skill = SDDSpecSkill()
    print(json.dumps(skill.info(), indent=2))
