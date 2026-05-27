#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
N8N Skill - Workflow automation
Uso: Crear y gestionar workflows de automatización con N8N API
"""
import json
import requests
from typing import Dict, List, Any

class N8NSkill:
    def __init__(self, api_url: str = "http://localhost:5678", api_key: str = ""):
        self.name = "N8NSkill"
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.available = self._check_available()
    
    def _check_available(self) -> bool:
        try:
            r = requests.get(f"{self.api_url}/health", timeout=3)
            return r.status_code == 200
        except:
            return False
    
    def _headers(self) -> Dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-N8N-API-KEY"] = self.api_key
        return headers
    
    def create_workflow(self, name: str, nodes: List[Dict], connections: Dict = None) -> str:
        """Crea un nuevo workflow"""
        workflow = {
            "name": name,
            "nodes": nodes,
            "connections": connections or {},
            "active": False
        }
        
        try:
            r = requests.post(
                f"{self.api_url}/rest/workflows",
                json=workflow,
                headers=self._headers(),
                timeout=10
            )
            if r.status_code in [200, 201]:
                return f"[OK] Workflow '{name}' creado. ID: {r.json().get('id')}"
            return f"[ERROR] {r.status_code}: {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def activate_workflow(self, workflow_id: str) -> str:
        try:
            r = requests.post(
                f"{self.api_url}/rest/workflows/{workflow_id}/activate",
                headers=self._headers(),
                timeout=10
            )
            return f"[OK] Workflow activado" if r.status_code == 200 else f"[ERROR] {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def list_workflows(self) -> str:
        try:
            r = requests.get(f"{self.api_url}/rest/workflows", headers=self._headers(), timeout=10)
            if r.status_code == 200:
                workflows = r.json().get("data", [])
                return json.dumps([{"id": w["id"], "name": w["name"], "active": w["active"]} for w in workflows], indent=2)
            return f"[ERROR] {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def execute_workflow(self, workflow_id: str, data: Dict = None) -> str:
        try:
            r = requests.post(
                f"{self.api_url}/rest/workflows/{workflow_id}/run",
                json=data or {},
                headers=self._headers(),
                timeout=30
            )
            return f"[OK] Workflow ejecutado. Run ID: {r.json().get('id')}" if r.status_code == 200 else f"[ERROR] {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def create_web_scraper_workflow(self, url: str, output_file: str = "output.json") -> Dict:
        """Genera un workflow para scraper una web"""
        return {
            "name": "Web Scraper",
            "nodes": [
                {
                    "id": "1",
                    "name": "Cron",
                    "type": "n8n-nodes-base.cron",
                    "parameters": {"rule": {"interval": [{"field": "hours", "value": 1}]}}
                },
                {
                    "id": "2",
                    "name": "HTTP Request",
                    "type": "n8n-nodes-base.httpRequest",
                    "parameters": {"url": url, "method": "GET"}
                },
                {
                    "id": "3",
                    "name": "Guardar",
                    "type": "n8n-nodes-base.writeFile",
                    "parameters": {"fileName": output_file, "dataPropertyName": "json"}
                }
            ],
            "connections": {
                "Cron": {"main": [{"node": "HTTP Request", "type": "main", "index": 0}]},
                "HTTP Request": {"main": [{"node": "Guardar", "type": "main", "index": 0}]}
            }
        }
    
    def create_social_media_workflow(self, platforms: List[str] = None) -> Dict:
        """Genera workflow para publicar en redes sociales"""
        platforms = platforms or ["twitter", "linkedin"]
        nodes = [{"id": "1", "name": "Trigger", "type": "n8n-nodes-base.manualTrigger"}]
        
        for i, platform in enumerate(platforms, start=2):
            nodes.append({
                "id": str(i),
                "name": platform.title(),
                "type": f"n8n-nodes-base.{platform}"
            })
        
        return {"name": "Social Media Post", "nodes": nodes, "connections": {}}
    
    def info(self) -> Dict:
        return {
            "skill": self.name,
            "available": self.available,
            "api_url": self.api_url,
            "docs": "https://docs.n8n.io",
            "install": "npm install n8n -g  o  docker run -p 5678:5678 n8nio/n8n"
        }

if __name__ == "__main__":
    skill = N8NSkill()
    print(json.dumps(skill.info(), indent=2))
