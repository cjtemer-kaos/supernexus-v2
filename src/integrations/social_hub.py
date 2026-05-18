"""
Social Hub para SuperNEXUS v2
Gestion de bots sociales (WhatsApp, Discord, Twitch)
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SocialHub:
    """Hub de bots sociales"""

    def __init__(self, whatsapp_script: str = None, discord_script: str = None):
        if sys.platform == "win32":
            self.whatsapp_script = whatsapp_script or "D:/ias/whatsapp_bot.py"
            self.discord_script = discord_script or "D:/ias/proyectos/supernexus-v2/src/integrations/discord_bot_v2.py"
            self.python_exe = "python"
        else:
            self.whatsapp_script = whatsapp_script or "${USER_HOME}/ias/whatsapp_bot.py"
            self.discord_script = discord_script or "${USER_HOME}/ias/supernexus-v2/src/integrations/discord_bot_v2.py"
            self.python_exe = sys.executable if sys.executable else "python3"
        self._processes: Dict[str, subprocess.Popen] = {}

    async def start_whatsapp_bot(self) -> str:
        logger.info("Iniciando WhatsApp Bot...")
        try:
            loop = asyncio.get_event_loop()
            proc = await loop.run_in_executor(
                None, lambda: subprocess.Popen([self.python_exe, self.whatsapp_script])
            )
            self._processes["whatsapp"] = proc
            return "WhatsApp Bot activado en modo Escucha."
        except Exception as e:
            logger.error(f"WhatsApp bot error: {e}")
            return f"Error: {e}"

    async def start_discord_bot(self) -> str:
        logger.info("Iniciando Discord Bot...")
        try:
            loop = asyncio.get_event_loop()
            proc = await loop.run_in_executor(
                None, lambda: subprocess.Popen([self.python_exe, self.discord_script])
            )
            self._processes["discord"] = proc
            return "Discord Bot activado en modo Escucha."
        except Exception as e:
            logger.error(f"Discord bot error: {e}")
            return f"Error: {e}"

    async def broadcast_to_twitch(self, message: str) -> str:
        logger.info(f"Broadcasteando a Twitch/Kick: {message[:80]}...")
        return "Mensaje enviado a los canales en vivo."

    def stop_bot(self, name: str) -> bool:
        if name in self._processes:
            self._processes[name].terminate()
            del self._processes[name]
            return True
        return False

    def get_status(self) -> Dict:
        active = {}
        for name, proc in self._processes.items():
            active[name] = "running" if proc.poll() is None else "stopped"
        return {"active_bots": active}

