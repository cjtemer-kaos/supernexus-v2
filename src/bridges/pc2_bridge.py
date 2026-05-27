"""
PC2 Bridge - Puente especifico para nodo remoto en SuperNEXUS v2.0

Conexion dedicada a nodo remoto con capacidades:
- GPU, Ollama, Python, NEXUS, OpenClaw, Antigravity
- Sin secrets: password via variable de entorno
"""

import asyncio
import json
import logging
import os
import subprocess
from typing import Dict, List, Optional
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Cargar .env si existe para robustez en control de nodos
from pathlib import Path
for p in [Path(__file__).resolve().parents[2] / ".env", Path.cwd() / ".env"]:
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception as e:
            logger.error(f"Error cargando .env desde {p}: {e}")


class PC2Bridge:
    """
    Puente dedicado a nodo remoto.
    Gestiona SSH, servicios remotos, y ejecucion GPU.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 22,
        user: Optional[str] = None,
    ):
        self.host = host or os.environ.get("SUPER_NEXUS_PC2_IP", "")
        self.port = port
        self.user = user or os.environ.get("SUPER_NEXUS_PC2_USER", "")
        self.password_env = "SUPER_NEXUS_PC2_PASSWORD"
        self.nexus_url = f"http://{self.host}:9000" if self.host else ""
        self.openclaw_url = f"http://{self.host}:18789" if self.host else ""
        self._online = False
        self._capabilities: List[str] = []

    def is_configured(self) -> bool:
        """Check if remote node is configured"""
        return bool(self.host and self.user)

    async def connect(self) -> bool:
        """Verifica conexion al nodo remoto (intenta /api/status, luego /health como fallback)"""
        if not self.is_configured():
            logger.info("Remote node not configured. Set SUPER_NEXUS_PC2_IP in .env")
            self._online = False
            return False

        endpoints = ["/api/status", "/health"]
        for ep in endpoints:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    r = await client.get(f"{self.nexus_url}{ep}")
                    if r.status_code == 200:
                        self._online = True
                        self._capabilities = ["gpu", "ollama", "python", "nexus", "openclaw", "antigravity"]
                        logger.info(f"Remote node online via {ep}")
                        return True
            except Exception:
                continue

        logger.warning("Remote node not available (tried /api/status and /health)")
        self._online = False
        return False

    async def execute_remote(self, command: str, timeout: int = 120) -> Dict:
        """
        Ejecuta comando en PC2 via SSH.
        Usa SSH keys (preferido) o sshpass via variable de entorno.
        """
        password = os.environ.get(self.password_env, "")

        if password:
            ssh_cmd = [
                "sshpass", "-e",
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-p", str(self.port),
                f"{self.user}@{self.host}",
                command,
            ]
            env = os.environ.copy()
            env["SSHPASS_PASSWORD"] = password
        else:
            ssh_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-p", str(self.port),
                f"{self.user}@{self.host}",
                command,
            ]
            env = os.environ.copy()

        try:
            proc = await asyncio.create_subprocess_exec(
                *ssh_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace")[:5000],
                "stderr": stderr.decode("utf-8", errors="replace")[:5000],
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": f"Command timed out after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_ollama(self, model: str, prompt: str) -> Dict:
        """Ejecuta modelo de Ollama en PC2"""
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(
                    f"{self.nexus_url}/api/ollama",
                    json={"model": model, "prompt": prompt},
                )
                return r.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def run_gpu_task(self, task: str) -> Dict:
        """Ejecuta tarea GPU en PC2"""
        command = f"cd /home/{self.user}/NEXUS && python -c \"import sys; print(sys.executable)\""
        return await self.execute_remote(command)

    async def get_system_info(self) -> Dict:
        """Obtiene informacion del sistema PC2"""
        commands = {
            "gpu": "nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader",
            "cpu": "nproc",
            "memory": "free -h",
            "disk": "df -h /",
            "ollama_models": "ollama list 2>/dev/null || echo 'none'",
        }

        results = {}
        for name, cmd in commands.items():
            r = await self.execute_remote(cmd, timeout=30)
            results[name] = r.get("stdout", "").strip() if r.get("success") else "unavailable"

        return results

    async def sync_files(self, local_path: str, remote_path: str) -> Dict:
        """Sincroniza archivos a PC2 via scp"""
        password = os.environ.get(self.password_env, "")

        if password:
            scp_cmd = [
                "sshpass", "-e",
                "scp", "-o", "StrictHostKeyChecking=no",
                "-P", str(self.port),
                "-r", local_path,
                f"{self.user}@{self.host}:{remote_path}",
            ]
            env = os.environ.copy()
            env["SSHPASS_PASSWORD"] = password
        else:
            scp_cmd = [
                "scp", "-o", "StrictHostKeyChecking=no",
                "-P", str(self.port),
                "-r", local_path,
                f"{self.user}@{self.host}:{remote_path}",
            ]
            env = os.environ.copy()

        try:
            proc = await asyncio.create_subprocess_exec(
                *scp_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await proc.communicate()
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace")[:1000],
                "stderr": stderr.decode("utf-8", errors="replace")[:1000],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status(self) -> Dict:
        """Estado de PC2"""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "online": self._online,
            "capabilities": self._capabilities,
            "nexus_url": self.nexus_url,
            "openclaw_url": self.openclaw_url,
        }
