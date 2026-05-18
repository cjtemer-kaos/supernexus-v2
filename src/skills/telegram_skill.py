# NEXUS TELEGRAM - Remote Control Skill
"""
Skill para control remoto de Nexus vía Telegram Bot.
Inspirado en la autopsia de JARVIS-HRZ v2.0.
"""

import os
import requests
from typing import Dict

class TelegramSkill:
    def __init__(self):
        self.name = "TelegramControl"
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.api_url = f"https://api.telegram.org/bot{self.token}"

    def info(self) -> Dict:
        return {
            "name": self.name,
            "status": "Ready" if self.token else "Missing Token",
            "methods": ["send_notification", "get_updates", "send_status"]
        }

    def send_notification(self, message: str):
        """Envía una notificación al usuario."""
        if not self.token or not self.chat_id:
            return "Error: Token o Chat ID no configurados."
        
        payload = {
            "chat_id": self.chat_id,
            "text": f"🤖 **NEXUS ALERT**\n\n{message}",
            "parse_mode": "Markdown"
        }
        try:
            r = requests.post(f"{self.api_url}/sendMessage", json=payload)
            return r.json()
        except Exception as e:
            return f"Error enviando Telegram: {e}"

    def send_status(self):
        """Envía el estado actual de los nodos (${USERNAME}/Remote Node)."""
        # Aquí se integraría con el monitor de salud
        status_msg = "✅ **${USERNAME} (Local):** ONLINE (X3D 7950)\n✅ **Remote Node (Remote):** ONLINE (Ryzen 2600 + GPU)"
        return self.send_notification(status_msg)

# Instancia para el manager
telegram_skill = TelegramSkill()
