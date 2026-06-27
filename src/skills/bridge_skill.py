import json
import os
import time

class BridgeSkill:
    def __init__(self):
        self.name = "bridge"
        self.description = "Puente de comunicación entre Nexus IA y OpenCode para tareas autónomas."
        self.bridge_path = os.getenv("NEXUS_BRIDGE_PATH", str(Path.home() / ".nexus" / "bridge.json"))

    def read_tasks(self) -> list:
        """Lee tareas pendientes del puente."""
        if not os.path.exists(self.bridge_path):
            return []
        
        try:
            with open(self.bridge_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get("tasks", [])
        except:
            return []

    def add_task(self, task: str, model: str = "minimax/m2.5") -> str:
        """Agrega una nueva tarea al puente."""
        task_id = str(int(time.time()))
        if not os.path.exists(self.bridge_path):
            data = {"tasks": [], "status": "RUNNING"}
        else:
            try:
                with open(self.bridge_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except:
                data = {"tasks": [], "status": "RUNNING"}
        
        if "tasks" not in data:
            data["tasks"] = []
            
        new_task = {
            "id": task_id,
            "task": task,
            "model": model,
            "status": "pending",
            "timestamp": time.ctime()
        }
        data["tasks"].append(new_task)
        
        with open(self.bridge_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return task_id

    def update_task_status(self, task_id: str, status: str, result: str = None) -> bool:
        """Actualiza el estado de una tarea en el puente."""
        if not os.path.exists(self.bridge_path):
            return False
            
        try:
            with open(self.bridge_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for task in data.get("tasks", []):
                if task.get("id") == task_id:
                    task["status"] = status
                    if result:
                        task["result"] = result
                    break
            
            with open(self.bridge_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True
        except:
            return False

    def info(self) -> dict:
        return {
            "skill": self.name,
            "bridge_file": self.bridge_path,
            "methods": ["read_tasks()", "add_task(task, model)", "update_task_status(id, status, result)"]
        }

def get_skill():
    return BridgeSkill()
