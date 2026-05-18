"""
Task Scheduler para SuperNEXUS v2
Programacion de tareas periodicas con soporte async
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class NexusScheduler:
    """Scheduler de tareas async"""

    def __init__(self, jobs_file: str = None):
        self.jobs_file = Path(jobs_file or Path.home() / ".nexus" / "scheduled_jobs.json")
        self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        self.active = False
        self.jobs = self._load_jobs()
        self._task = None
        self._handlers: Dict[str, Callable] = {}

    def _load_jobs(self) -> list:
        if self.jobs_file.exists():
            try:
                return json.loads(self.jobs_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_jobs(self):
        self.jobs_file.write_text(json.dumps(self.jobs, indent=4), encoding="utf-8")

    def add_job(self, name: str, interval_minutes: int, task_description: str,
                gem: str = "scholar", handler: Callable = None) -> Dict:
        job = {
            "name": name, "interval": interval_minutes,
            "task": task_description, "gem": gem,
            "last_run": None, "enabled": True,
        }
        self.jobs.append(job)
        self._save_jobs()
        if handler:
            self._handlers[name] = handler
        logger.info(f"Job added: {name} (every {interval_minutes}m)")
        return job

    def register_handler(self, name: str, handler: Callable):
        self._handlers[name] = handler

    async def _run_job(self, job: Dict):
        logger.info(f"Executing scheduled task: {job['name']}")
        job['last_run'] = datetime.now().isoformat()
        self._save_jobs()

        if job['name'] in self._handlers:
            handler = self._handlers[job['name']]
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(job['task'])
                else:
                    handler(job['task'])
            except Exception as e:
                logger.error(f"Job {job['name']} error: {e}")

    async def start(self):
        self.active = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Nexus Scheduler started")

    async def _run_loop(self):
        while self.active:
            now = datetime.now()
            for job in self.jobs:
                if not job.get("enabled", True):
                    continue
                last_run = job.get("last_run")
                if last_run:
                    last_dt = datetime.fromisoformat(last_run)
                    elapsed = (now - last_dt).total_seconds() / 60
                    if elapsed < job["interval"]:
                        continue
                await self._run_job(job)
            await asyncio.sleep(30)

    def stop(self):
        self.active = False
        if self._task:
            self._task.cancel()
        logger.info("Nexus Scheduler stopped")

    def list_jobs(self) -> List[Dict]:
        return self.jobs

    def remove_job(self, name: str) -> bool:
        self.jobs = [j for j in self.jobs if j["name"] != name]
        self._save_jobs()
        self._handlers.pop(name, None)
        return True

    def get_status(self) -> Dict:
        return {
            "active": self.active,
            "jobs_count": len(self.jobs),
            "jobs": [{"name": j["name"], "interval": j["interval"],
                      "last_run": j.get("last_run"), "enabled": j.get("enabled", True)}
                     for j in self.jobs],
        }
