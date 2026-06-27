"""
Nexus Guardian para SuperNEXUS v2
Seguridad, validacion de configs, backups y auditoria
"""

import asyncio
import json
import logging
import shutil
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NexusGuardian:
    """Guardian de seguridad y backups"""

    def __init__(self, base_dir: str = None, backups_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent.parent
        self.backups_dir = Path(backups_dir) if backups_dir else self.base_dir / "brain" / "backups"
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def validate_json(self, file_path: str) -> Tuple[bool, str]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True, "JSON Valido"
        except json.JSONDecodeError as e:
            return False, f"Error de sintaxis en JSON: {str(e)}"
        except Exception as e:
            return False, f"Error leyendo archivo: {str(e)}"

    def create_backup(self, file_path: str) -> Tuple[bool, str]:
        src = Path(file_path)
        if not src.exists():
            return False, "El archivo no existe"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = src.stem
        backup_path = self.backups_dir / f"{filename}.{timestamp}.bak"

        try:
            shutil.copy2(str(src), str(backup_path))
            logger.info(f"Backup creado: {backup_path}")
            return True, str(backup_path)
        except Exception as e:
            logger.error(f"Error creando backup: {e}")
            return False, f"Error creando backup: {str(e)}"

    async def check_remote_port(self, host: str, port: int, timeout: float = 3.0) -> Tuple[Optional[bool], str]:
        loop = asyncio.get_event_loop()

        def _check():
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    return True, f"Puerto {port} en {host} esta ABIERTO"
            except (socket.timeout, ConnectionRefusedError):
                return False, f"Puerto {port} en {host} esta CERRADO (Seguro)"
            except Exception as e:
                return None, f"Error de conexion: {str(e)}"

        return await loop.run_in_executor(None, _check)

    async def full_security_audit(self, config_files: List[str], remote_host: str = None) -> str:
        report = []
        for f in config_files:
            valid, msg = self.validate_json(f)
            icon = "OK" if valid else "FAIL"
            report.append(f"[ARCHIVO] {Path(f).name}: [{icon}] {msg}")

        if remote_host:
            critical_ports = [22, 80, 443, 28015, 28016]
            for p in critical_ports:
                open_port, msg = await self.check_remote_port(remote_host, p)
                icon = "WARN" if open_port else "OK"
                report.append(f"[PUERTO] {remote_host}:{p}: [{icon}] {msg}")

        return "\n".join(report)

    def list_backups(self) -> List[Dict]:
        backups = []
        for f in sorted(self.backups_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file():
                backups.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                })
        return backups

    def get_status(self) -> Dict:
        return {
            "backups_dir": str(self.backups_dir),
            "backups_count": len(list(self.backups_dir.iterdir())) if self.backups_dir.exists() else 0,
        }
