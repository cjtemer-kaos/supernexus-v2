"""
Sub-Agent Spawner - Delegacion de tareas a sub-agentes para SuperNEXUS v2

Crea sub-agentes dinamicos para tareas complejas que pueden descomponerse.
Inspirado en el patron delegate_tool de hermes-agent.

Caracteristicas:
- ThreadPool dinamico con depth limit MAX=3
- Cada sub-agente tiene contexto aislado
- Resultados se agregan al agente padre
- Timeout y cancellation por sub-agente
- Resource limits por sub-agente

Patrones extraidos de: hermes-agent/agent/tools/delegate.py
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

logger = logging.getLogger("nexus-subagent")


class SubAgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class SubAgentResult:
    """Resultado de un sub-agente"""
    agent_id: str
    task: str
    status: SubAgentStatus
    result: Any = None
    error: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0
    tokens_used: int = 0


@dataclass
class SubAgentSpec:
    """Especificacion de un sub-agente"""
    task: str
    gem: str = "auto"  # Gema asignada
    context: str = ""
    timeout_seconds: float = 300
    max_retries: int = 0
    priority: int = 1  # 1-5, 5 = mas prioritario


class SubAgentSpawner:
    """
    Gestor de sub-agentes con delegacion dinamica.

    Uso:
        spawner = SubAgentSpawner(executor=director.execute)
        results = await spawner.spawn_parallel([
            SubAgentSpec(task="analizar codigo", gem="code"),
            SubAgentSpec(task="buscar documentacion", gem="scholar"),
        ])
    """

    MAX_DEPTH = 3  # Limite maximo de delegacion en cascada
    MAX_CONCURRENT = 5  # Maximo sub-agentes concurrentes

    def __init__(
        self,
        executor: Callable = None,
        max_depth: int = MAX_DEPTH,
        max_concurrent: int = MAX_CONCURRENT,
    ):
        self.executor = executor
        self.max_depth = max_depth
        self.max_concurrent = max_concurrent
        self._active_agents: Dict[str, SubAgentResult] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stats = {
            "total_spawned": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_cancelled": 0,
            "total_timeout": 0,
            "total_duration_ms": 0,
        }

    async def spawn_parallel(self, specs: List[SubAgentSpec], depth: int = 1) -> List[SubAgentResult]:
        """
        Ejecuta multiples sub-agentes en paralelo.

        Args:
            specs: Lista de especificaciones de sub-agentes
            depth: Nivel de delegacion actual (para evitar recursion infinita)

        Returns:
            Lista de resultados de sub-agentes
        """
        if depth > self.max_depth:
            logger.warning(f"Max delegation depth reached ({self.max_depth}), aborting")
            return [
                SubAgentResult(
                    agent_id="depth_limit",
                    task=spec.task,
                    status=SubAgentStatus.FAILED,
                    error=f"Max delegation depth exceeded ({self.max_depth})",
                )
                for spec in specs
            ]

        if not self.executor:
            logger.error("No executor configured for sub-agent spawning")
            return [
                SubAgentResult(
                    agent_id="no_executor",
                    task=spec.task,
                    status=SubAgentStatus.FAILED,
                    error="No executor configured",
                )
                for spec in specs
            ]

        # Ordenar por prioridad (mayor primero)
        sorted_specs = sorted(specs, key=lambda s: s.priority, reverse=True)

        # Ejecutar en paralelo con semaphore
        tasks = [self._run_subagent(spec, depth) for spec in sorted_specs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Procesar resultados
        final_results = []
        for r in results:
            if isinstance(r, Exception):
                final_results.append(SubAgentResult(
                    agent_id="error",
                    task="",
                    status=SubAgentStatus.FAILED,
                    error=str(r),
                ))
            else:
                final_results.append(r)

        return final_results

    async def spawn_sequential(self, specs: List[SubAgentSpec], depth: int = 1) -> List[SubAgentResult]:
        """
        Ejecuta sub-agentes secuencialmente (cada uno puede usar resultado del anterior).

        Args:
            specs: Lista de especificaciones
            depth: Nivel de delegacion

        Returns:
            Lista de resultados en orden
        """
        results = []
        for spec in specs:
            result = await self._run_subagent(spec, depth)
            results.append(result)
            # Si fallo y no hay retries, detener
            if result.status == SubAgentStatus.FAILED and spec.max_retries == 0:
                break
        return results

    async def _run_subagent(self, spec: SubAgentSpec, depth: int) -> SubAgentResult:
        """Ejecuta un sub-agente individual"""
        agent_id = str(uuid.uuid4())[:8]
        self._stats["total_spawned"] += 1

        result = SubAgentResult(
            agent_id=agent_id,
            task=spec.task,
            status=SubAgentStatus.PENDING,
        )
        self._active_agents[agent_id] = result

        async with self._semaphore:
            result.status = SubAgentStatus.RUNNING
            result.started_at = datetime.now().isoformat()
            start = time.time()

            logger.info(f"Sub-agent started: {agent_id} (gem: {spec.gem}, depth: {depth})")
            logger.info(f"  Task: {spec.task[:100]}")

            try:
                # Ejecutar con timeout
                if asyncio.iscoroutinefunction(self.executor):
                    task_result = await asyncio.wait_for(
                        self.executor(spec.task, gem=spec.gem, context=spec.context),
                        timeout=spec.timeout_seconds,
                    )
                else:
                    task_result = self.executor(spec.task, gem=spec.gem, context=spec.context)

                result.status = SubAgentStatus.COMPLETED
                result.result = task_result
                if isinstance(task_result, dict):
                    result.tokens_used = task_result.get("tokens_used", 0)

                self._stats["total_completed"] += 1
                logger.info(f"Sub-agent completed: {agent_id}")

            except asyncio.TimeoutError:
                result.status = SubAgentStatus.TIMEOUT
                result.error = f"Timeout after {spec.timeout_seconds}s"
                self._stats["total_timeout"] += 1
                logger.warning(f"Sub-agent timeout: {agent_id}")

            except asyncio.CancelledError:
                result.status = SubAgentStatus.CANCELLED
                self._stats["total_cancelled"] += 1
                logger.info(f"Sub-agent cancelled: {agent_id}")

            except Exception as e:
                result.status = SubAgentStatus.FAILED
                result.error = str(e)
                self._stats["total_failed"] += 1
                logger.error(f"Sub-agent failed: {agent_id} - {e}")

                # Reintentar si esta configurado
                if spec.max_retries > 0:
                    logger.info(f"Retrying sub-agent {agent_id} ({spec.max_retries} retries left)")
                    spec.max_retries -= 1
                    await asyncio.sleep(1)
                    return await self._run_subagent(spec, depth)

            finally:
                result.completed_at = datetime.now().isoformat()
                result.duration_ms = (time.time() - start) * 1000
                self._stats["total_duration_ms"] += result.duration_ms
                self._active_agents.pop(agent_id, None)

        return result

    def cancel_agent(self, agent_id: str) -> bool:
        """Cancela un sub-agente activo"""
        if agent_id in self._active_agents:
            self._active_agents[agent_id].status = SubAgentStatus.CANCELLED
            self._stats["total_cancelled"] += 1
            return True
        return False

    def cancel_all(self):
        """Cancela todos los sub-agentes activos"""
        for agent_id in list(self._active_agents.keys()):
            self.cancel_agent(agent_id)

    def get_active_agents(self) -> Dict[str, SubAgentResult]:
        """Obtiene sub-agentes activos"""
        return dict(self._active_agents)

    def get_stats(self) -> Dict:
        return {
            **self._stats,
            "active_agents": len(self._active_agents),
            "max_depth": self.max_depth,
            "max_concurrent": self.max_concurrent,
            "avg_duration_ms": (
                self._stats["total_duration_ms"] / max(1, self._stats["total_completed"] + self._stats["total_failed"])
            ),
        }
