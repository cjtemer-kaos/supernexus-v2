"""
SSH Bridge - Conexion SSH a maquinas remotas

Permite ejecutar comandos y enviar tareas a maquinas remotas via SSH.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SSHMachine:
    """Configuracion de una maquina remota"""
    name: str
    host: str
    user: str
    port: int = 22
    capabilities: list = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


class SSHBridge:
    """
    Bridge SSH para ejecutar comandos en maquinas remotas.
    Usa subprocess con ssh/scp para evitar dependencias de paramiko.
    """

    def __init__(self):
        self.machines: Dict[str, SSHMachine] = {}
        self._load_known_machines()

    def _load_known_machines(self):
        """Carga maquinas conocidas (sin passwords hardcodeados)"""
        Remote Node_ip = os.getenv("SUPER_NEXUS_Remote Node_IP", "")
        Remote Node_user = os.getenv("SUPER_NEXUS_Remote Node_USER", "")

        if Remote Node_ip and Remote Node_user:
            self.machines["remote"] = SSHMachine(
                name="remote",
                host=Remote Node_ip,
                user=Remote Node_user,
                capabilities=["gpu", "ollama", "python", "nexus", "openclaw", "antigravity"],
            )

    async def execute(self, machine: str, command: str, timeout: int = 60) -> Dict[str, Any]:
        """Ejecuta comando en maquina remota via SSH"""
        if machine not in self.machines:
            return {"success": False, "error": f"Machine '{machine}' not found"}

        m = self.machines[machine]
        ssh_cmd = f"ssh {m.user}@{m.host} -p {m.port} {command}"

        try:
            proc = await asyncio.create_subprocess_shell(
                ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip(),
                "returncode": proc.returncode,
                "machine": machine,
                "command": command,
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def check_health(self, machine: str) -> bool:
        """Verifica si la maquina esta accesible"""
        result = await self.execute(machine, "echo pong", timeout=5)
        return result.get("success", False)

    async def get_nexus_status(self, machine: str) -> Dict:
        """Verifica estado de NEXUS en maquina remota"""
        result = await self.execute(machine, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:9000/", timeout=5)
        return {
            "machine": machine,
            "nexus_online": result.get("stdout") == "200",
            "raw": result,
        }

    def list_machines(self) -> Dict[str, list]:
        """Lista maquinas disponibles con sus capacidades"""
        return {name: m.capabilities for name, m in self.machines.items()}
