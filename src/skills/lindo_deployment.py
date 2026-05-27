import requests
import os
import json
import sys

# Agregar el directorio raíz al path para importar la config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

class LindoSkill:
    """
    Skill para el despliegue automático de sitios web usando la API de Lindo AI.
    Especialmente diseñada para ser orquestada por la gema Producer.
    """
    
    def __init__(self):
        self.api_key = config.LINDO_API_KEY
        self.base_url = "https://api.lindo.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_website(self, name, description, template_id=None):
        """
        Crea un nuevo sitio web basado en un prompt de IA o template.
        """
        if not self.api_key:
            return "[ERROR] Lindo API Key no configurada en config.py"
            
        url = f"{self.base_url}/ai/workspace/website"
        payload = {
            "name": name,
            "description": description
        }
        if template_id:
            payload["templateId"] = template_id
            
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return f"[ERROR] Error al crear sitio: {str(e)}"

    def get_websites(self):
        """
        Lista todos los sitios web en el workspace.
        """
        url = f"{self.base_url}/websites"
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return f"[ERROR] Error al listar sitios: {str(e)}"

    def get_analytics(self, website_id):
        """
        Obtiene métricas de tráfico para un sitio específico.
        """
        url = f"{self.base_url}/analytics/website/{website_id}"
        try:
            response = requests.get(url, headers=self.headers)
            return response.json()
        except Exception as e:
            return f"[ERROR] Error al obtener analíticas: {str(e)}"

if __name__ == "__main__":
    # Test simple
    skill = LindoSkill()
    print("Skill de Lindo AI cargada. Esperando órdenes del Director.")
