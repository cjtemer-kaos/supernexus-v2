#!/usr/bin/env python3
"""SDD Propose Skill - Propuestas de cambio"""
import json

class SDDProposeSkill:
    def __init__(self):
        self.name = "sdd_propose"
        self.description = "Crear propuesta con alcance"
    
    def create_proposal(self, change_name: str, description: str = "") -> dict:
        return {
            "proposal": {
                "change_name": change_name,
                "description": description,
                "scope": "to_define",
                "priority": "medium",
                "dependencies": [],
                "risks": []
            }
        }
    
    def run(self, change_name: str = "", output_file: str = "") -> str:
        return json.dumps(self.create_proposal(change_name), indent=2)
    
    def info(self) -> dict:
        return {"skill": self.name, "description": self.description}

if __name__ == "__main__":
    print(json.dumps(SDDProposeSkill().info(), indent=2))