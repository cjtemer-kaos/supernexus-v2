import asyncio
import httpx
import json

OLLAMA_URL = "http://localhost:11434/api/generate"

class ParallelDelegateSkill:
    """
    Skill para delegar tareas en paralelo a múltiples modelos locales (Ollama).
    Inspirado en la lógica de trabajo paralela de DeepSeek y Verdent.
    """
    
    def info(self):
        return {
            "name": "Parallel Delegate",
            "description": "Delegación de tareas concurrentes a modelos locales para ahorro de tokens.",
            "methods": ["run_parallel", "ask_experts"]
        }

    async def _call_ollama(self, model, task):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    OLLAMA_URL,
                    json={"model": model, "prompt": task, "stream": False},
                    timeout=120.0
                )
                if response.status_code == 200:
                    return {"model": model, "response": response.json().get("response", "")}
            except Exception as e:
                return {"model": model, "error": str(e)}
        return {"model": model, "error": "Unknown error"}

    async def run_parallel(self, tasks):
        """
        tasks: list of dicts {"model": "...", "task": "..."}
        """
        jobs = [self._call_ollama(t["model"], t["task"]) for t in tasks]
        results = await asyncio.gather(*jobs)
        return results

    def ask_experts(self, task_ui, task_logic):
        """Método de conveniencia para tareas típicas de Nexus"""
        tasks = [
            {"model": "qwen2.5-coder", "task": f"Genera el código UI para: {task_ui}"},
            {"model": "deepseek-r1", "task": f"Analiza la lógica de negocio para: {task_logic}"}
        ]
        # Como este es un skill que se llama desde un entorno síncrono usualmente, 
        # proporcionamos una forma de ejecutar el loop.
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run_parallel(tasks))

if __name__ == "__main__":
    # Prueba rápida
    skill = ParallelDelegateSkill()
    print("Iniciando prueba de delegación paralela...")
    # Esto es solo un ejemplo de cómo se llamaría
