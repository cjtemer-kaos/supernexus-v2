"""
Resource Monitor para SuperNEXUS v2
Monitoreo de CPU, RAM y GPU
"""

import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


def get_system_stats() -> Dict:
    """Retorna uso de CPU, RAM, disco y uptime con nombres compatibles UI"""
    import time
    stats = {"cpu": 0, "ram": 0, "gpu": 0, "safe": True,
             "cpu_percent": 0, "memory_percent": 0, "memory_used": "0 MB",
             "disk_percent": 0, "disk_used": "0 GB", "uptime_seconds": 0}
    if not PSUTIL_AVAILABLE:
        return stats
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        boot = psutil.boot_time()
        stats["cpu"] = cpu
        stats["cpu_percent"] = cpu
        stats["ram"] = mem.percent
        stats["memory_percent"] = mem.percent
        stats["memory_used"] = f"{mem.used // (1024**2)} MB"
        stats["gpu"] = 0
        stats["disk_percent"] = disk.percent
        stats["disk_used"] = f"{disk.used // (1024**3)} GB"
        stats["uptime_seconds"] = int(time.time() - boot)
        if cpu > 80 or mem.percent > 85:
            stats["safe"] = False
    except Exception as e:
        logger.error(f"Stats error: {e}")
    return stats


def is_safe_to_run_local(threshold: float = 75) -> Tuple[bool, float, float]:
    stats = get_system_stats()
    is_safe = stats["cpu"] < threshold and stats["ram"] < threshold
    return is_safe, stats["cpu"], stats["ram"]
