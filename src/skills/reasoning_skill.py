import subprocess
import json

class ReasoningSkill:
    """
    Habilidad de Razonamiento Crítico (Pensamiento Profundo).
    Utiliza Gemma 4 local para validar arquitecturas y decisiones antes de la ejecución.
    """
    def __init__(self, model="gemma4:latest"):
        self.model = model
        self.name = "reasoning_engine"

    def think(self, context, task):
        """
        Ejecuta un bucle de razonamiento profundo sobre una tarea.
        """
        prompt = f"""
        [MODO RAZONAMIENTO NEXUS - GEMMA 4]
        CONTEXTO ACTUAL: {context}
        TAREA A REALIZAR: {task}
        
        INSTRUCCIONES:
        1. Analiza posibles fallos o cuellos de botella.
        2. Optimiza el flujo para máxima productividad (x10).
        3. Verifica la consistencia con los estándares de los Mentores (Prompt Mastery, NVIDIA).
        4. Propón la mejor arquitectura de nodos/skills.
        
        RESPUESTA:
        """
        try:
            result = subprocess.run(
                ["ollama", "run", self.model, prompt],
                capture_output=True, text=True, encoding="utf-8"
            )
            return {"status": "SUCCESS", "reasoning": result.stdout.strip()}
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

if __name__ == "__main__":
    engine = ReasoningSkill()
    print(json.dumps(engine.think("Refactorización x10", "Integrar Flux en Nexus"), indent=2))
