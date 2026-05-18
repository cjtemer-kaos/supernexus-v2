"""
System Optimizer para SuperNEXUS v2
Afinidad de CPU y optimizacion de recursos
"""

import asyncio
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil no disponible. pip install psutil")


class SystemOptimizer:
    """Optimizador de sistema async"""

    def __init__(self, target_process: str = "python.exe", target_script: str = "main.py",
                 vcache_cores: list = None):
        self.target_process = target_process
        self.target_script = target_script
        self.vcache_cores = vcache_cores or list(range(8))
        self.last_stats = {"cpu": 0, "ram": 0, "gpu": 0}
        self._running = False
        self._task = None

    def optimize_affinity(self):
        if not PSUTIL_AVAILABLE:
            return
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline'] or []
                if any(self.target_script in arg for arg in cmdline):
                    p = psutil.Process(proc.info['pid'])
                    if p.cpu_affinity() != self.vcache_cores:
                        p.cpu_affinity(self.vcache_cores)
                        for child in p.children(recursive=True):
                            try:
                                child.cpu_affinity(self.vcache_cores)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        logger.info(f"CPU affinity optimized for PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def update_stats(self) -> Dict:
        if not PSUTIL_AVAILABLE:
            return self.last_stats
        self.last_stats["cpu"] = psutil.cpu_percent(interval=None)
        self.last_stats["ram"] = psutil.virtual_memory().percent
        try:
            self.last_stats["disk"] = psutil.disk_usage("D:\\").percent
        except Exception:
            self.last_stats["disk"] = 0
        return self.last_stats

    async def start(self, interval: int = 5):
        self._running = True
        self._task = asyncio.create_task(self._run_loop(interval))
        logger.info("SystemOptimizer started")

    async def _run_loop(self, interval: int):
        while self._running:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.optimize_affinity)
                self.update_stats()
            except Exception as e:
                logger.error(f"Optimizer error: {e}")
            await asyncio.sleep(interval)

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("SystemOptimizer stopped")

    def get_stats(self) -> Dict:
        return self.last_stats
