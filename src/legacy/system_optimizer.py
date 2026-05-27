import psutil
import threading
import time
import os
import logging

# --- CONFIGURACIÓN DE OPTIMIZACIÓN NEXUS ---
TARGET_PROCESS_NAME = "python.exe" # El proceso que corre nexus.py
TARGET_SCRIPT_NAME = "nexus.py"
VCACHE_CORES = list(range(8)) # Núcleos 0-7 (3D V-Cache en 5700X3D)

class SystemOptimizer(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True
        self.running = True
        self.last_stats = {"cpu": 0, "ram": 0, "gpu": 0}
        self.logger = logging.getLogger("NexusOptimizer")

    def run(self):
        self.logger.info("[*] Servicio de Optimización Nexus Iniciado.")
        while self.running:
            try:
                self.optimize_affinity()
                self.update_stats()
            except Exception as e:
                self.logger.error(f"Error en optimizador: {e}")
            time.sleep(5)

    def optimize_affinity(self):
        """Busca el proceso del backend y sus hilos para fijarlos a V-Cache."""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline'] or []
                if any(TARGET_SCRIPT_NAME in arg for arg in cmdline):
                    # Encontrado el proceso backend
                    p = psutil.Process(proc.info['pid'])
                    if p.cpu_affinity() != VCACHE_CORES:
                        p.cpu_affinity(VCACHE_CORES)
                        # También a los hijos (Ollama spawns, etc.)
                        for child in p.children(recursive=True):
                            child.cpu_affinity(VCACHE_CORES)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def update_stats(self):
        """Actualiza estadísticas sin bloquear el hilo principal."""
        self.last_stats["cpu"] = psutil.cpu_percent(interval=None)
        self.last_stats["ram"] = psutil.virtual_memory().percent
        # Disk usage de D:
        try:
            self.last_stats["disk"] = psutil.disk_usage("D:\\").percent
        except:
            self.last_stats["disk"] = 0

    def get_stats(self):
        return self.last_stats

    def stop(self):
        self.running = False
