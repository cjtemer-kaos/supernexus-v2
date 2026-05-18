import os
import json
from pathlib import Path

class GridPlannerSkill:
    """
    Skill para implementar el bucle Think-Plan-Execute.
    Claude genera el plan, y esta skill lo coordina con la Grid.
    """
    def __init__(self):
        nexus_home = os.getenv("NEXUS_HOME", str(Path.home() / ".nexus"))
        self.plan_path = os.path.join(nexus_home, "PLAN.md")

    def execute_plan(self, node="auto"):
        """
        Lee el PLAN.md actual y lo envía a la Grid para ejecución.
        """
        if not os.path.exists(self.plan_path):
            return "No se encontró PLAN.md"

        with open(self.plan_path, "r", encoding="utf-8") as f:
            plan_content = f.read()

        print(f"[*] Enviando plan a la Grid (Nodo: {node})...")

        # Enviar el plan completo como una tarea para OpenCode
        task = f"Ejecuta el siguiente plan de acción:\n\n{plan_content}"

        result = call_opencode({
            "task": task,
            "node": node,
            "model": "minimax-m2.5",
            "workspace": str(Path.cwd())
        })

        return result

def grid_planner():
    planner = GridPlannerSkill()
    return planner.execute_plan()
