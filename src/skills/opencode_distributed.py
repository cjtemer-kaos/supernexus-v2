import requests
import json
import concurrent.futures
from pathlib import Path
import sys

# NEXUS IA Master Configuration Integration
nexus_master_path = Path(__file__).parent.parent / "NEXUS_MASTER"
if str(nexus_master_path) not in sys.path:
    sys.path.insert(0, str(nexus_master_path))
from nexus_config_manager import NexusConfigManager

class OpenCodeGridSkill:
    def __init__(self):
        self.config = NexusConfigManager()
        self.nodes = self.config.get('OPENCODE_GRID.nodes')

    def execute_grid_task(self, tasks_map):
        """
        tasks_map: { "local": ["task1", "task2"], "Remote Node": ["task3"] }
        """
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_node = {}
            for node_name, tasks in tasks_map.items():
                if node_name in self.nodes:
                    url = self.nodes[node_name]
                    for task in tasks:
                        future = executor.submit(self._run_remote, url, task)
                        future_to_node[future] = f"{node_name}: {task[:20]}..."
            
            for future in concurrent.futures.as_completed(future_to_node):
                node_task = future_to_node[future]
                try:
                    data = future.result()
                    results[node_task] = data
                except Exception as exc:
                    results[node_task] = {"error": str(exc)}
                    
        return results

    def _run_remote(self, url, task):
        try:
            r = requests.post(url, json={"task": task}, timeout=600)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

def distribute_opencode(params):
    """Nexus Skill Entry Point"""
    grid = OpenCodeGridSkill()
    
    # If it's a list of tasks, distribute them
    tasks = params.get("tasks", [])
    if not tasks:
        # Single task? Use local
        task = params.get("task")
        if task:
            tasks = [task]
        else:
            return {"error": "Please provide 'tasks' (list) or 'task' (string) to execute."}
    
    # Simple distribution: alternate nodes
    tasks_map = {"local": [], "Remote Node": []}
    for i, t in enumerate(tasks):
        node = "local" if i % 2 == 0 else "Remote Node"
        tasks_map[node].append(t)
        
    results = grid.execute_grid_task(tasks_map)
    return {"status": "completed", "results": results}
