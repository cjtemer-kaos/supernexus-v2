#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trigger.dev Skill - Background jobs
Uso: Crear y gestionar trabajos en segundo plano con Trigger.dev
"""
import json
import requests
from typing import Dict, Any, List

class TriggerSkill:
    def __init__(self, api_key: str = "", endpoint: str = "https://api.trigger.dev"):
        self.name = "TriggerSkill"
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')
    
    def _headers(self) -> Dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else {}
        }
    
    def create_job(self, name: str, task_type: str = "scheduled", config: Dict = None) -> str:
        """Crea un nuevo job en Trigger.dev"""
        job = {
            "name": name,
            "type": task_type,
            "config": config or {}
        }
        
        if task_type == "scheduled":
            job["schedule"] = config.get("schedule", "0 0 * * *")  # Diario por defecto
        elif task_type == "event":
            job["event"] = config.get("event", "user.created")
        
        try:
            r = requests.post(
                f"{self.endpoint}/v1/jobs",
                json=job,
                headers=self._headers(),
                timeout=10
            )
            if r.status_code in [200, 201]:
                return f"[OK] Job '{name}' creado. ID: {r.json().get('id')}"
            return f"[ERROR] {r.status_code}: {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def list_jobs(self) -> str:
        try:
            r = requests.get(f"{self.endpoint}/v1/jobs", headers=self._headers(), timeout=10)
            if r.status_code == 200:
                jobs = r.json().get("jobs", [])
                return json.dumps([{"id": j["id"], "name": j["name"], "status": j["status"]} for j in jobs], indent=2)
            return f"[ERROR] {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def trigger_job(self, job_id: str, payload: Dict = None) -> str:
        try:
            r = requests.post(
                f"{self.endpoint}/v1/jobs/{job_id}/trigger",
                json=payload or {},
                headers=self._headers(),
                timeout=30
            )
            return f"[OK] Job ejecutado" if r.status_code == 200 else f"[ERROR] {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def generate_job_code(self, job_name: str, task_description: str) -> str:
        """Genera código para un job de Trigger.dev"""
        code = f"""import {{ eventTrigger, intervalTrigger }} from "@trigger.dev/sdk";

export const {job_name} = eventTrigger({{
  id: "{job_name}",
  name: "{job_name.replace('_', ' ').title()}",
  on: {{
    // Tu lógica aquí
    // Ejemplo: procesar datos, enviar emails, etc.
  }},
}});

// O para tareas programadas:
export const {job_name}Scheduled = intervalTrigger({{
  id: "{job_name}-scheduled",
  name: "{job_name.replace('_', ' ').title()} Scheduled",
  interval: {{ seconds: 3600 }}, // Cada hora
  run: async (event, ctx) => {{
    console.log("{task_description}");
    // Tu lógica aquí
  }},
}});
"""
        return f"[CODE]\n{code}"
    
    def generate_setup(self) -> str:
        """Genera archivo de configuración"""
        config = """export default {
  project: process.env.TRIGGER_PROJECT_ID!,
  apiKey: process.env.TRIGGER_API_KEY!,
  apiUrl: process.env.TRIGGER_API_URL,
};"""
        return f"[CODE]\n{config}"
    
    def info(self) -> Dict:
        return {
            "skill": self.name,
            "description": "Background jobs y tareas programadas",
            "install": "npm install @trigger.dev/sdk",
            "docs": "https://docs.trigger.dev",
            "endpoint": self.endpoint
        }

if __name__ == "__main__":
    skill = TriggerSkill()
    print(json.dumps(skill.info(), indent=2))
