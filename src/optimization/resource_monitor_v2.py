"""
ResourceMonitor v2 - Monitor de recursos mejorado para SuperNEXUS v2.0

Características:
- Monitor de recursos en tiempo real (CPU, RAM, GPU, Disco, Red)
- Predicción de uso de recursos por tipo de tarea
- Alertas automáticas cuando se superan umbrales
- Historial de métricas para análisis de tendencias
"""

import psutil
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

try:
    import subprocess
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ResourceMetrics:
    """Métricas de recursos en un momento dado"""
    timestamp: str
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    gpu_percent: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    disk_percent: float = 0.0
    network_sent_mb: float = 0.0
    network_recv_mb: float = 0.0
    process_count: int = 0


@dataclass
class TaskResourceProfile:
    """Perfil de recursos para un tipo de tarea"""
    task_type: str
    avg_cpu: float
    avg_ram_mb: float
    avg_gpu: float
    estimated_duration_s: float
    confidence: float = 0.0


class ResourceMonitor:
    """
    Monitor de recursos mejorado con predicción y alertas.
    """
    
    def __init__(
        self,
        cpu_threshold: float = 80.0,
        ram_threshold: float = 85.0,
        gpu_threshold: float = 90.0,
        history_size: int = 1000,
    ):
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.gpu_threshold = gpu_threshold
        
        self.history: deque = deque(maxlen=history_size)
        self.task_profiles: Dict[str, TaskResourceProfile] = {}
        self._alert_callbacks = []
        self._last_network = psutil.net_io_counters()
        self._last_network_time = time.time()
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Obtiene métricas actuales"""
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        net = psutil.net_io_counters()
        now = time.time()
        time_delta = now - self._last_network_time
        
        net_sent_mb = (net.bytes_sent - self._last_network.bytes_sent) / (1024 * 1024)
        net_recv_mb = (net.bytes_recv - self._last_network.bytes_recv) / (1024 * 1024)
        
        self._last_network = net
        self._last_network_time = now
        
        gpu_percent = 0.0
        gpu_memory_used_mb = 0.0
        gpu_memory_total_mb = 0.0
        
        if GPU_AVAILABLE:
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(", ")
                    gpu_percent = float(parts[0])
                    gpu_memory_used_mb = float(parts[1])
                    gpu_memory_total_mb = float(parts[2])
            except:
                pass
        
        metrics = ResourceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu,
            ram_percent=ram.percent,
            ram_used_gb=ram.used / (1024**3),
            ram_total_gb=ram.total / (1024**3),
            gpu_percent=gpu_percent,
            gpu_memory_used_mb=gpu_memory_used_mb,
            gpu_memory_total_mb=gpu_memory_total_mb,
            disk_percent=disk.percent,
            network_sent_mb=net_sent_mb,
            network_recv_mb=net_recv_mb,
            process_count=len(psutil.pids()),
        )
        
        self.history.append(metrics)
        
        self._check_alerts(metrics)
        
        return metrics
    
    def is_safe_to_run(self, threshold: float = None) -> bool:
        """Verifica si es seguro ejecutar tareas intensivas"""
        threshold = threshold or self.cpu_threshold
        metrics = self.get_current_metrics()
        
        return (
            metrics.cpu_percent < threshold and
            metrics.ram_percent < self.ram_threshold and
            metrics.gpu_percent < self.gpu_threshold
        )
    
    def predict_resources(self, task_type: str) -> Optional[TaskResourceProfile]:
        """Predice uso de recursos para un tipo de tarea"""
        if task_type in self.task_profiles:
            return self.task_profiles[task_type]
        
        profiles = {
            "chat": TaskResourceProfile("chat", 15.0, 512.0, 0.0, 5.0, 0.8),
            "code_generation": TaskResourceProfile("code_generation", 35.0, 1024.0, 10.0, 30.0, 0.7),
            "image_generation": TaskResourceProfile("image_generation", 25.0, 2048.0, 85.0, 60.0, 0.6),
            "video_processing": TaskResourceProfile("video_processing", 50.0, 4096.0, 90.0, 120.0, 0.5),
            "training": TaskResourceProfile("training", 70.0, 8192.0, 95.0, 600.0, 0.4),
            "research": TaskResourceProfile("research", 20.0, 768.0, 5.0, 45.0, 0.7),
        }
        
        return profiles.get(task_type)
    
    def record_task_execution(self, task_type: str, actual_cpu: float, actual_ram_mb: float, actual_gpu: float, duration_s: float):
        """Registra ejecución real para mejorar predicciones"""
        if task_type not in self.task_profiles:
            self.task_profiles[task_type] = TaskResourceProfile(
                task_type, actual_cpu, actual_ram_mb, actual_gpu, duration_s, 0.5
            )
        else:
            profile = self.task_profiles[task_type]
            alpha = 0.3
            profile.avg_cpu = alpha * actual_cpu + (1 - alpha) * profile.avg_cpu
            profile.avg_ram_mb = alpha * actual_ram_mb + (1 - alpha) * profile.avg_ram_mb
            profile.avg_gpu = alpha * actual_gpu + (1 - alpha) * profile.avg_gpu
            profile.estimated_duration_s = alpha * duration_s + (1 - alpha) * profile.estimated_duration_s
            profile.confidence = min(1.0, profile.confidence + 0.1)
    
    def add_alert_callback(self, callback):
        """Agrega callback para alertas"""
        self._alert_callbacks.append(callback)
    
    def _check_alerts(self, metrics: ResourceMetrics):
        """Verifica y dispara alertas"""
        alerts = []
        
        if metrics.cpu_percent > self.cpu_threshold:
            alerts.append(f"CPU usage high: {metrics.cpu_percent:.1f}%")
        
        if metrics.ram_percent > self.ram_threshold:
            alerts.append(f"RAM usage high: {metrics.ram_percent:.1f}%")
        
        if metrics.gpu_percent > self.gpu_threshold:
            alerts.append(f"GPU usage high: {metrics.gpu_percent:.1f}%")
        
        if alerts:
            for callback in self._alert_callbacks:
                try:
                    callback(alerts, metrics)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
    
    def get_history(self, minutes: int = 60) -> List[Dict]:
        """Obtiene historial de métricas"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        
        return [
            {
                "timestamp": m.timestamp,
                "cpu_percent": m.cpu_percent,
                "ram_percent": m.ram_percent,
                "gpu_percent": m.gpu_percent,
                "disk_percent": m.disk_percent,
            }
            for m in self.history
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]
    
    def get_trends(self, minutes: int = 60) -> Dict:
        """Calcula tendencias de uso"""
        history = self.get_history(minutes)
        
        if not history:
            return {"trend": "no_data"}
        
        cpu_values = [h["cpu_percent"] for h in history]
        ram_values = [h["ram_percent"] for h in history]
        
        cpu_avg = sum(cpu_values) / len(cpu_values)
        ram_avg = sum(ram_values) / len(ram_values)
        
        cpu_trend = "increasing" if len(cpu_values) > 1 and cpu_values[-1] > cpu_values[0] else "decreasing"
        ram_trend = "increasing" if len(ram_values) > 1 and ram_values[-1] > ram_values[0] else "decreasing"
        
        return {
            "cpu": {
                "avg": cpu_avg,
                "min": min(cpu_values),
                "max": max(cpu_values),
                "trend": cpu_trend,
            },
            "ram": {
                "avg": ram_avg,
                "min": min(ram_values),
                "max": max(ram_values),
                "trend": ram_trend,
            },
            "period_minutes": minutes,
            "samples": len(history),
        }
    
    def get_status(self) -> Dict:
        """Obtiene estado completo"""
        metrics = self.get_current_metrics()
        trends = self.get_trends()
        
        return {
            "current": {
                "cpu_percent": metrics.cpu_percent,
                "ram_percent": metrics.ram_percent,
                "ram_used_gb": metrics.ram_used_gb,
                "ram_total_gb": metrics.ram_total_gb,
                "gpu_percent": metrics.gpu_percent,
                "disk_percent": metrics.disk_percent,
                "network_sent_mb": metrics.network_sent_mb,
                "network_recv_mb": metrics.network_recv_mb,
                "process_count": metrics.process_count,
            },
            "trends": trends,
            "task_profiles": {
                name: {
                    "avg_cpu": p.avg_cpu,
                    "avg_ram_mb": p.avg_ram_mb,
                    "avg_gpu": p.avg_gpu,
                    "estimated_duration_s": p.estimated_duration_s,
                    "confidence": p.confidence,
                }
                for name, p in self.task_profiles.items()
            },
            "safe_to_run": self.is_safe_to_run(),
        }
