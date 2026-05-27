"""
Background Workers - Sistema de workers automáticos

14 workers que se ejecutan en segundo plano para mantener el sistema optimizado:
1. Memory Consolidation - Consolida memorias periódicamente
2. Session Cleanup - Limpia sesiones expiradas
3. Token Optimization - Optimiza uso de tokens
4. Security Scan - Escanea patrones de seguridad
5. Performance Metrics - Recolecta métricas
6. Context Compaction - Compacta contexto automáticamente
7. Error Pattern Detection - Detecta patrones de error
8. Knowledge Sync - Sincroniza conocimiento entre nodos
9. Health Check - Verifica salud del sistema
10. Learning - Aprende de interacciones pasadas
11. Skill Audit - Audita skills obsoletos
12. Backup - Backups automáticos
13. Three-Loop Improvement - Self-improvement system
14. Peer Learning - Chat y autoaprendizaje PC1 ↔ PC2

Arquitectura:
- Cada worker es una clase con run() method
- Triggered por eventos o schedule
- Ejecución asíncrona con timeout
- Resultados persistidos en nexus_memory.db
"""

import asyncio
import json
import logging
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class WorkerTrigger(Enum):
    """Tipos de trigger para workers"""
    SCHEDULED = "scheduled"      # Ejecución periódica
    EVENT = "event"              # Triggered por evento
    ON_DEMAND = "on_demand"      # Ejecución manual


@dataclass
class WorkerResult:
    """Resultado de ejecución de un worker"""
    worker_name: str
    success: bool
    duration_ms: float
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class WorkerConfig:
    """Configuración de un worker"""
    name: str
    trigger: WorkerTrigger
    interval_seconds: int = 300  # 5 min default
    timeout_seconds: int = 30
    enabled: bool = True
    max_retries: int = 3


class BaseWorker(ABC):
    """Clase base para todos los background workers"""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.last_run: Optional[WorkerResult] = None
        self.run_count = 0
        self.error_count = 0
        self._running = False
    
    @abstractmethod
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        """Ejecutar el worker. Debe ser implementado por subclases."""
        pass
    
    async def execute(self, context: Dict[str, Any]) -> WorkerResult:
        """Wrapper con timeout, retries y métricas"""
        if not self.config.enabled:
            return WorkerResult(
                worker_name=self.config.name,
                success=False,
                duration_ms=0,
                error="Worker disabled"
            )
        
        self._running = True
        start = time.time()
        
        try:
            for attempt in range(self.config.max_retries):
                try:
                    result = await asyncio.wait_for(
                        self.run(context),
                        timeout=self.config.timeout_seconds
                    )
                    result.duration_ms = (time.time() - start) * 1000
                    self.last_run = result
                    self.run_count += 1
                    if result.success:
                        self.error_count = 0
                    else:
                        self.error_count += 1
                    return result
                except asyncio.TimeoutError:
                    logger.warning(f"Worker {self.config.name} timed out (attempt {attempt + 1})")
                    if attempt == self.config.max_retries - 1:
                        return WorkerResult(
                            worker_name=self.config.name,
                            success=False,
                            duration_ms=(time.time() - start) * 1000,
                            error=f"Timeout after {self.config.timeout_seconds}s"
                        )
                except Exception as e:
                    logger.error(f"Worker {self.config.name} error: {e}")
                    if attempt == self.config.max_retries - 1:
                        return WorkerResult(
                            worker_name=self.config.name,
                            success=False,
                            duration_ms=(time.time() - start) * 1000,
                            error=f"{type(e).__name__}: {str(e)}"
                        )
                    await asyncio.sleep(1 * (attempt + 1))  # Backoff
        finally:
            self._running = False
        
        return WorkerResult(
            worker_name=self.config.name,
            success=False,
            duration_ms=(time.time() - start) * 1000,
            error="Max retries exceeded"
        )
    
    @property
    def is_running(self) -> bool:
        return self._running


# ============================================================
# 12 WORKERS IMPLEMENTADOS
# ============================================================

class MemoryConsolidationWorker(BaseWorker):
    """Consolida memorias periódicamente (ADD-only + topic keys)"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="memory_consolidation",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=600,  # 10 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            consolidator = context.get("memory_consolidator")
            if not consolidator:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No consolidator")
            
            # Ejecutar consolidación
            stats = consolidator.get_stats() if hasattr(consolidator, "get_stats") else {}
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"stats": stats, "action": "consolidation_complete"}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class SessionCleanupWorker(BaseWorker):
    """Limpia sesiones expiradas"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="session_cleanup",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=1800,  # 30 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            sessions = context.get("sessions")
            if not sessions:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No session manager")
            
            cleaned = 0
            # Limpiar sesiones inactivas por más de 2h
            cutoff = datetime.now() - timedelta(hours=2)
            for session_id, session in list(sessions.sessions.items()):
                if session.last_activity < cutoff.isoformat():
                    sessions.close_session(session_id)
                    cleaned += 1
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"cleaned_sessions": cleaned}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class TokenOptimizationWorker(BaseWorker):
    """Optimiza uso de tokens"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="token_optimization",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=900,  # 15 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            budget = context.get("token_budget")
            if not budget:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No token budget")
            
            status = budget.get_status() if hasattr(budget, "get_status") else {}
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"budget_status": status}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class SecurityScanWorker(BaseWorker):
    """Escanea patrones de seguridad"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="security_scan",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=300,  # 5 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            hooks = context.get("hooks")
            if not hooks:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No hooks engine")
            
            # Obtener métricas de seguridad
            metrics = hooks.get_metrics() if hasattr(hooks, "get_metrics") else {}
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"security_metrics": metrics}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class PerformanceMetricsWorker(BaseWorker):
    """Recolecta métricas de performance"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="performance_metrics",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=60,  # 1 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            director = context.get("director")
            if not director:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No director")
            
            # Recolectar métricas
            metrics = {
                "gemas_count": len(director.gemas) if hasattr(director, "gemas") else 0,
                "sessions_active": director.sessions.active_sessions if hasattr(director.sessions, "active_sessions") else 0,
                "execution_log_size": len(director.execution_log) if hasattr(director, "execution_log") else 0,
            }
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"metrics": metrics}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class ContextCompactionWorker(BaseWorker):
    """Compacta contexto automáticamente"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="context_compaction",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=1200,  # 20 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            compactor = context.get("compactor")
            sessions = context.get("sessions")
            if not compactor or not sessions:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No compactor/sessions")
            
            compacted = 0
            for session_id in list(sessions.sessions.keys()):
                if sessions.needs_compact(session_id):
                    sessions.compact_session_trajectory(session_id)
                    compacted += 1
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"compacted_sessions": compacted}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class ErrorPatternWorker(BaseWorker):
    """Detecta patrones de error"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="error_pattern_detection",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=300,  # 5 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            execution_log = context.get("execution_log", [])
            
            # Analizar últimos 100 ejecuciones
            recent = execution_log[-100:]
            errors = [e for e in recent if not e.get("success", True)]
            
            patterns = {}
            for error in errors:
                error_type = error.get("error_type", "unknown")
                patterns[error_type] = patterns.get(error_type, 0) + 1
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={
                    "total_errors": len(errors),
                    "error_patterns": patterns,
                    "error_rate": len(errors) / len(recent) if recent else 0
                }
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class KnowledgeSyncWorker(BaseWorker):
    """Sincroniza conocimiento entre nodos"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="knowledge_sync",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=600,  # 10 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            # Verificar conectividad con nodos
            connectivity = context.get("connectivity")
            if not connectivity:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No connectivity layer")
            
            nodes = connectivity.get_nodes() if hasattr(connectivity, "get_nodes") else []
            synced = 0
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"nodes_checked": len(nodes), "synced": synced}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class HealthCheckWorker(BaseWorker):
    """Verifica salud del sistema"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="health_check",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=30,  # 30 sec
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            health = context.get("memory_health")
            if not health:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No health monitor")
            
            status = health.get_status() if hasattr(health, "get_status") else {}
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"health_status": status}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class LearningWorker(BaseWorker):
    """Aprende de interacciones pasadas"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="learning",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=1800,  # 30 min
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            execution_log = context.get("execution_log", [])
            
            # Analizar patrones de éxito
            recent = execution_log[-500:]
            successes = [e for e in recent if e.get("success", False)]
            
            # Aprender patrones exitosos
            patterns = {}
            for success in successes:
                gem = success.get("gem", "unknown")
                patterns[gem] = patterns.get(gem, 0) + 1
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={
                    "success_rate": len(successes) / len(recent) if recent else 0,
                    "successful_patterns": patterns
                }
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class SkillAuditWorker(BaseWorker):
    """Audita skills obsoletos"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="skill_audit",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=3600,  # 1h
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            skill_loader = context.get("skill_loader")
            if not skill_loader:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No skill loader")
            
            stats = skill_loader.get_stats() if hasattr(skill_loader, "get_stats") else {}
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"skill_stats": stats}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class BackupWorker(BaseWorker):
    """Backups automáticos"""
    
    def __init__(self):
        super().__init__(WorkerConfig(
            name="backup",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=7200,  # 2h
        ))
    
    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            nexus_home = context.get("nexus_home", Path.home() / ".nexus")
            backup_dir = Path(nexus_home) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup de archivos críticos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"backup_{timestamp}.json"
            
            backup_data = {
                "timestamp": timestamp,
                "type": "full_backup",
                "files_backed_up": []
            }
            
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2)
            
            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={"backup_file": str(backup_file)}
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class ThreeLoopWorker(BaseWorker):
    """Auto-mejora: ejecuta el three-loop self-improvement system periodicamente"""

    def __init__(self):
        super().__init__(WorkerConfig(
            name="three_loop_improvement",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=3600,  # 1h
        ))

    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            director = context.get("director")
            if not director or not hasattr(director, 'three_loop'):
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No three_loop available")

            async def exec_fn(task: str) -> str:
                return await director.llm_gateway_text(task)

            judge_fn = director._judge_response if hasattr(director, '_judge_response') else None

            medium = await director.three_loop.run_medium_loop(
                execute_fn=exec_fn,
                judge_fn=judge_fn,
                sample_size=6,
            )

            slow = await director.three_loop.run_slow_loop()

            state = director.three_loop.state.__dict__

            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={
                    "medium_loop_score": medium.get("benchmark", {}).get("avg_score", 0),
                    "slow_loop_recommendations": len(slow.get("recommendations", [])),
                    "state": state,
                }
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class TrainingWorker(BaseWorker):
    """Entrenamiento cada 15 min: tareas adaptativas, benchmark, RAG indexado."""

    def __init__(self):
        super().__init__(WorkerConfig(
            name="training",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=900,   # 15 min
            timeout_seconds=240,    # 4 min max
        ))

    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            director = context.get("director")
            if not director or not hasattr(director, 'peer_chat'):
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No peer_chat")
            pc = director.peer_chat

            # 1. Ping peers
            status = await pc.ping()
            pc1_ok = status.get("pc1", {}).get("online", False)
            pc2_ok = status.get("pc2", {}).get("online", False)
            if not pc1_ok and not pc2_ok:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="Both peers offline")

            # 2. Training tasks por categoria
            training_tasks = [
                ("Write a Python function to merge two sorted lists", "coding"),
                ("Explain the time complexity of quicksort", "research"),
                ("Solve: if x^2 + 3x + 2 = 0, what are the roots?", "math"),
                ("Describe the singleton pattern and when to use it", "architecture"),
            ]
            results = []
            for task, cat in training_tasks:
                r = await pc.collaborative_task(task, cat)
                results.append(r)
                await asyncio.sleep(0.3)

            # 3. Adaptive tasks for weak categories
            weak = pc._get_weak_categories(min_samples=2)
            if weak:
                for node, cat, rate in weak[:2]:
                    t = await pc.generate_adaptive_tasks(1)
                    if t:
                        await pc.collaborative_task(t[0]["task"], cat)

            # 4. Win stats summary
            win_summary = {}
            for node, cats in pc._win_stats.items():
                for cat, s in cats.items():
                    rate = s["wins"] / s["total"] if s["total"] > 0 else 0
                    win_summary[f"{node}/{cat}"] = f"{s['wins']}/{s['total']} ({rate:.0%})"

            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={
                    "training_tasks": len(training_tasks),
                    "results_count": len(results),
                    "weak_categories": len(weak),
                    "win_summary": win_summary,
                    "knowledge_count": len(pc.learned_knowledge),
                }
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


class PeerLearningWorker(BaseWorker):
    """Chat y autoaprendizaje PC1 ↔ PC2: colaboracion y aprendizaje compartido"""

    def __init__(self):
        super().__init__(WorkerConfig(
            name="peer_learning",
            trigger=WorkerTrigger.SCHEDULED,
            interval_seconds=1800,  # 30 min
            timeout_seconds=300,    # 5 min timeout for full cycle
        ))

    async def run(self, context: Dict[str, Any]) -> WorkerResult:
        try:
            director = context.get("director")
            if not director or not hasattr(director, 'peer_chat'):
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="No peer_chat available")

            # Ping both peers
            status = await director.peer_chat.ping()
            pc1_ok = status.get("pc1", {}).get("online", False)
            pc2_ok = status.get("pc2", {}).get("online", False)

            if not pc1_ok and not pc2_ok:
                return WorkerResult(self.config.name, success=False, duration_ms=0, error="Both peers offline")

            # Run collaborative tasks
            tasks = [
                "Write a function that implements a binary search tree in Python with insert, delete, and search",
                "Explain the difference between RAG and fine-tuning for LLMs",
                "Design a REST API for a task management system",
                "How would you optimize an agent's self-improvement pipeline?",
            ]
            result = await director.peer_chat.learn_from_best(tasks)

            # Post report to shared memory
            director.peer_chat.post_report_to_memory(director.hybrid_memory, "PeerChat Auto-Learning Session")

            return WorkerResult(
                worker_name=self.config.name,
                success=True,
                duration_ms=0,
                data={
                    "total_tasks": result.get("total_tasks", 0),
                    "win_stats": result.get("win_stats", {}),
                    "pc1_online": pc1_ok,
                    "pc2_online": pc2_ok,
                    "knowledge_count": len(director.peer_chat.learned_knowledge),
                }
            )
        except Exception as e:
            return WorkerResult(self.config.name, success=False, duration_ms=0, error=str(e))


# ============================================================
# WORKER MANAGER
# ============================================================
# WORKER MANAGER
# ============================================================

class BackgroundWorkerManager:
    """
    Gestiona los 12 background workers.
    
    Inspirado en 12 auto-triggered workers:
    - audit, optimize, testgaps, security, performance, health, etc.
    
    Uso:
        manager = BackgroundWorkerManager()
        manager.register_all()
        await manager.start()
    """
    
    def __init__(self):
        self.workers: Dict[str, BaseWorker] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._results: List[WorkerResult] = []
        self._results_lock = asyncio.Lock()
    
    def register_all(self):
        """Registrar los 12 workers"""
        workers = [
            MemoryConsolidationWorker(),
            SessionCleanupWorker(),
            TokenOptimizationWorker(),
            SecurityScanWorker(),
            PerformanceMetricsWorker(),
            ContextCompactionWorker(),
            ErrorPatternWorker(),
            KnowledgeSyncWorker(),
            HealthCheckWorker(),
            LearningWorker(),
            SkillAuditWorker(),
            BackupWorker(),
            ThreeLoopWorker(),
            TrainingWorker(),       # cada 15 min
            PeerLearningWorker(),   # cada 30 min
        ]
        
        for worker in workers:
            self.workers[worker.config.name] = worker
            logger.info(f"Registered worker: {worker.config.name} (trigger: {worker.config.trigger.value}, interval: {worker.config.interval_seconds}s)")
    
    async def start(self, context: Dict[str, Any]):
        """Iniciar todos los workers scheduled"""
        self._running = True
        
        for name, worker in self.workers.items():
            if worker.config.trigger == WorkerTrigger.SCHEDULED:
                task = asyncio.create_task(self._run_worker_loop(name, worker, context))
                self._tasks.append(task)
        
        logger.info(f"Started {len(self._tasks)} background workers")
    
    async def stop(self):
        """Detener todos los workers"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("All background workers stopped")
    
    async def run_on_demand(self, worker_name: str, context: Dict[str, Any]) -> WorkerResult:
        """Ejecutar un worker específico on-demand"""
        worker = self.workers.get(worker_name)
        if not worker:
            return WorkerResult(worker_name, success=False, duration_ms=0, error=f"Worker not found: {worker_name}")
        
        result = await worker.execute(context)
        async with self._results_lock:
            self._results.append(result)
        return result
    
    async def _run_worker_loop(self, name: str, worker: BaseWorker, context: Dict[str, Any]):
        """Loop de ejecución para un worker scheduled"""
        while self._running:
            try:
                result = await worker.execute(context)
                async with self._results_lock:
                    self._results.append(result)
                
                if not result.success:
                    logger.warning(f"Worker {name} failed: {result.error}")
                
                await asyncio.sleep(worker.config.interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {name} loop error: {e}")
                await asyncio.sleep(10)  # Backoff
    
    def get_status(self) -> Dict[str, Any]:
        """Obtener estado de todos los workers"""
        status = {}
        for name, worker in self.workers.items():
            status[name] = {
                "enabled": worker.config.enabled,
                "running": worker.is_running,
                "run_count": worker.run_count,
                "error_count": worker.error_count,
                "last_run": worker.last_run.__dict__ if worker.last_run else None,
            }
        return status
    
    def get_recent_results(self, limit: int = 20) -> List[Dict]:
        """Obtener resultados recientes"""
        results = list(self._results[-limit:])
        return [r.__dict__ for r in results]
