"""
Nexus Suprawall - Deterministic Firewall for Agents
Defines granular permissions and actions for each agent within SuperNEXUS.
"""
from typing import List, Dict

class Suprawall:
    def __init__(self):
        # Default permissions mapped to agents
        self.permissions: Dict[str, List[str]] = {
            "claude-code": [
                "read_db", "write_db", "execute_python", "read_fs", "write_fs", "run_bash"
            ],
            "antigravity": [
                "read_db", "write_db", "execute_python", "read_fs", "write_fs", "run_bash", "orchestrate"
            ],
            "opencode": [
                "read_db", "write_db", "read_fs"
            ],
            "supernexus": [
                "read_db", "write_db", "orchestrate", "manage_nodes"
            ],
            "guest": [
                "read_db"
            ]
        }
        
        # Globally restricted capabilities
        self.restricted_skills = ["format_c", "delete_db", "shutdown_node"]

    def can_execute(self, agent_name: str, action: str) -> bool:
        """Verifies if an agent has the permission to perform an action"""
        if action in self.restricted_skills:
            return False
            
        allowed_actions = self.permissions.get(agent_name, self.permissions["guest"])
        
        if action in allowed_actions:
            return True
            
        return False

    def validate_task(self, agent_name: str, task_content: str) -> bool:
        """Validates a task using basic rules and heuristics"""
        task_lower = task_content.lower()
        if "borrar" in task_lower or "delete" in task_lower or "rm " in task_lower:
            return self.can_execute(agent_name, "write_fs")
            
        if "python" in task_lower or "script" in task_lower:
            return self.can_execute(agent_name, "execute_python")
            
        return True

# Singleton instance
wall = Suprawall()

def check_permission(agent: str, action: str) -> bool:
    return wall.can_execute(agent, action)

def validate_agent_task(agent: str, task: str) -> bool:
    return wall.validate_task(agent, task)
