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
    """Retorna uso de CPU, RAM y GPU"""
    stats = {"cpu": 0, "ram": 0, "gpu": 0, "safe": True}
    if not PSUTIL_AVAILABLE:
        return stats
    try:
        stats["cpu"] = psutil.cpu_percent(interval=0.1)
        stats["ram"] = psutil.virtual_memory().percent
        if stats["cpu"] > 80 or stats["ram"] > 85:
            stats["safe"] = False
    except Exception as e:
        logger.error(f"Stats error: {e}")
    return stats


def is_safe_to_run_local(threshold: float = 75) -> Tuple[bool, float, float]:
    stats = get_system_stats()
    is_safe = stats["cpu"] < threshold and stats["ram"] < threshold
    return is_safe, stats["cpu"], stats["ram"]
