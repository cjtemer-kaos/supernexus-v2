#!/usr/bin/env python3
import json

class SequentialThinkingSkill:
    def __init__(self):
        self.name = "sequential_thinking"
        self.description = "Implementa el protocolo de pensamiento secuencial para planificación y validación de tareas complejas."
        self.steps = []

    def plan(self, task: str, estimated_steps: int = 5):
        """Inicia un nuevo ciclo de pensamiento secuencial."""
        self.steps = []
        return {
            "status": "Thinking Started",
            "task": task,
            "target_steps": estimated_steps,
            "instruction": "Genera el primer paso lógico para resolver esta tarea."
        }

    def add_step(self, thought: str, action: str = None, observation: str = None):
        """Agrega un paso al proceso de razonamiento."""
        step_id = len(self.steps) + 1
        step = {
            "step": step_id,
            "thought": thought,
            "action": action,
            "observation": observation
        }
        self.steps.append(step)
        return f"[Step {step_id}] Procesado. Pensamiento: {thought}"

    def finalize(self):
        """Consolida el pensamiento y entrega el plan final."""
        summary = "\n".join([f"{s['step']}. {s['thought']}" for s in self.steps])
        return {
            "status": "Thinking Completed",
            "plan": self.steps,
            "summary": summary
        }

    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "methods": ["plan(task)", "add_step(thought, action, observation)", "finalize()"]
        }

if __name__ == "__main__":
    skill = SequentialThinkingSkill()
    print(json.dumps(skill.info(), indent=2))
