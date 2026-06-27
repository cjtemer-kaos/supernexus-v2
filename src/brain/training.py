"""Brain: Training — self-improvement loops, teacher distillation, peer learning.

El cerebro de NEXUS para mejorar sus propios modelos.

Capacidades:
    - Three-loop improvement (fast/medium/slow)
    - Model autopsy + distillation
    - Teacher-student distillation (Claude, FreeQwen, local)
    - PeerChat (PC1 <-> PC2 collaborative learning)
    - LLM judge para evaluar respuestas

Design:
    TrainingBrain recibe el director como owner y consulta:
        - owner.recursive_seed, owner.recursive_improvement
        - owner.three_loop, owner.model_autopsy
        - owner.peer_chat, owner.hybrid_memory
        - owner.llm_gateway
    Todos opcionales — degrada con dict de error si faltan.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


DEFAULT_PEER_TASKS = [
    "Write a Python function to merge two sorted linked lists",
    "Explain how to implement a RAG system from scratch",
    "Optimize a SQL query with 3 JOINs and a subquery",
    "Design a microservice architecture for real-time chat",
]

TEACHER_OUTPUT_DIR = Path.home() / ".nexus" / "autopsy"


class TrainingBrain:
    """Self-improvement, distillation, peer learning."""

    def __init__(self, owner: Any):
        self.owner = owner

    # ── Helpers ──────────────────────────────────────────────────────

    def _gateway(self):
        return getattr(self.owner, "llm_gateway", None)

    # ── Three-loop + improvement iteration ───────────────────────────

    async def run_improvement_iteration(
        self,
        sample_size: int = 10,
        generate_new: bool = True,
        use_judge: bool = True,
    ) -> Dict:
        improver = getattr(self.owner, "recursive_improvement", None)
        if improver is None:
            return {"error": "recursive_improvement not initialized"}
        judge_fn = self.judge_response if use_judge else None
        return await improver.run_iteration(
            execute_fn=self.llm_gateway_text,
            judge_fn=judge_fn,
            sample_size=sample_size,
            generate_new_examples=generate_new,
        )

    async def run_three_loops(self, sample_size: int = 30) -> Dict:
        three_loop = getattr(self.owner, "three_loop", None)
        if three_loop is None:
            return {"error": "three_loop not initialized"}
        judge_fn = self.judge_response

        async def exec_fn(task: str) -> str:
            return await self.llm_gateway_text(task)

        result = await three_loop.run_all_loops(
            execute_fn=exec_fn,
            judge_fn=judge_fn,
            sample_size=sample_size,
        )
        state = three_loop.state
        logger.info(
            f"Three-Loop complete. State: fast={state.fast_loop_count}, "
            f"medium={state.medium_loop_count}, slow={state.slow_loop_count}"
        )
        return result

    # ── Teacher providers + judge + gateway helper ───────────────────

    def register_teacher_providers(self) -> List[str]:
        """Loads .env keys and registers external teachers in llm_gateway.

        Returns: list of provider names successfully registered.
        """
        from dotenv import load_dotenv

        gateway = self._gateway()
        if gateway is None:
            return []

        project_root = getattr(self.owner, "_project_root", None) or "."
        load_dotenv(Path(project_root) / ".env", encoding="utf-8-sig")

        registered = []

        claude_key = os.getenv("ANTHROPIC_API_KEY", "")
        claude_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")
        if claude_key:
            gateway.add_provider(
                "claude", claude_url, api_key=claude_key,
                priority=2, timeout=120.0, cost_per_1m_tokens=15.0,
            )
            registered.append("claude")

        qwen_key = os.getenv("QWEN_API_KEY", "")
        if qwen_key:
            gateway.add_provider(
                "freeqwen", "http://localhost:3264/v1", api_key=qwen_key,
                priority=3, timeout=60.0,
            )
            registered.append("freeqwen")

        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if openrouter_key:
            gateway.add_provider(
                "openrouter", "https://openrouter.ai/api/v1", api_key=openrouter_key,
                priority=4, timeout=120.0, cost_per_1m_tokens=2.0,
            )
            registered.append("openrouter")

        for name in registered:
            logger.info(f"Teacher provider registered: {name}")
        return registered

    async def judge_response(self, prompt: str) -> Dict:
        """LLM-as-Judge. Robust to non-JSON / fenced output."""
        gateway = self._gateway()
        if gateway is None:
            return {"score": 0.5, "reasoning": "llm_gateway not initialized"}
        try:
            resp = await gateway.chat(
                messages=[{"role": "user", "content": prompt}],
                model="qwen2.5-coder:7b",
                temperature=0.1,
            )
            content = resp.content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                content = "\n".join(lines[1:-1]) if len(lines) > 2 else ""
                content = content.strip()
            if content.startswith("{"):
                return json.loads(content)
            logger.warning(f"Judge: could not parse response (started with {content[:30]})")
            return {"score": 0.5, "reasoning": "Could not parse judge response"}
        except Exception as e:
            logger.warning(f"Judge failed: {e}")
            return {"score": 0.5, "reasoning": str(e)}

    async def llm_gateway_text(self, prompt: str) -> str:
        """Bypass full Director pipeline — just route to llm_gateway."""
        gateway = self._gateway()
        if gateway is None:
            return ""
        try:
            resp = await gateway.chat(
                messages=[{"role": "user", "content": prompt}],
                model="qwen2.5-coder:7b",
            )
            return resp.content
        except Exception as e:
            logger.warning(f"LLM Gateway text failed: {e}")
            return ""

    # ── Model autopsy ────────────────────────────────────────────────

    async def run_model_autopsy(self, use_judge: bool = True) -> Dict:
        autopsy = getattr(self.owner, "model_autopsy", None)
        recursive_seed = getattr(self.owner, "recursive_seed", None)
        if autopsy is None or recursive_seed is None:
            return {"error": "model_autopsy or recursive_seed not initialized"}

        if use_judge:
            from src.core.recursive_seed_ai import JUDGE_PROMPT

            async def autopsy_judge(task: str, response: str) -> float:
                prompt = JUDGE_PROMPT.format(task=task, response=response)
                result = await self.judge_response(prompt)
                return float(result.get("score", 0.5))
            judge_fn = autopsy_judge
        else:
            judge_fn = None

        cm = await autopsy.full_scan(judge_fn=judge_fn)
        report = autopsy.generate_report()
        distill = await autopsy.distill_recursive_seed(
            rsai=recursive_seed,
            judge_fn=judge_fn,
        )
        report["distillation"] = distill
        logger.info(f"Autopsy complete. Best overall: {cm.overall_best_model}")
        return report

    # ── Teacher-student distillation (Claude / FreeQwen / local) ─────

    async def distill_from_teachers(
        self,
        tasks: List[str],
        categories: Optional[List[str]] = None,
    ) -> Dict:
        """Teacher distillation: probe many teachers, pick best response per task."""
        import httpx
        from dotenv import load_dotenv

        project_root = getattr(self.owner, "_project_root", None) or "."
        load_dotenv(Path(project_root) / ".env", encoding="utf-8-sig")

        TEACHER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = TEACHER_OUTPUT_DIR / "teacher_distillation.jsonl"
        examples: List[Dict] = []
        teacher_stats: Dict[str, Dict[str, int]] = {}

        def _bump(name: str, key: str):
            teacher_stats.setdefault(name, {"ok": 0, "fail": 0})[key] += 1

        for i, task in enumerate(tasks):
            cat = categories[i] if categories and i < len(categories) else "general"
            candidates: List[tuple] = []

            # 1. Local qwen-coder
            try:
                local = await self.llm_gateway_text(task)
                if local and len(local) > 50:
                    candidates.append(("qwen-coder (local)", local, len(local)))
                    _bump("qwen-coder", "ok")
                else:
                    _bump("qwen-coder", "fail")
            except Exception:
                _bump("qwen-coder", "fail")

            # 2. FreeQwenApi proxy (localhost:3264)
            try:
                async with httpx.AsyncClient(timeout=60) as c:
                    r = await c.post(
                        "http://localhost:3264/v1/chat/completions",
                        json={
                            "model": "qwen3-coder-plus",
                            "messages": [{"role": "user", "content": task}],
                            "max_tokens": 2048,
                        },
                        headers={
                            "Authorization": f"Bearer {os.getenv('QWEN_API_KEY', 'sk-free-qwen-proxy')}"
                        },
                    )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    candidates.append(("freeqwen (cloud)", content, len(content)))
                    _bump("freeqwen", "ok")
                else:
                    _bump("freeqwen", "fail")
            except Exception:
                _bump("freeqwen", "fail")

            # 3. Claude via opencode.ai/zen/v1 (OpenAI-compat)
            try:
                async with httpx.AsyncClient(timeout=120) as c:
                    r = await c.post(
                        "https://opencode.ai/zen/v1/chat/completions",
                        json={
                            "model": "claude-sonnet-4-20250514",
                            "max_tokens": 2048,
                            "messages": [{"role": "user", "content": task}],
                        },
                        headers={
                            "Authorization": f"Bearer {os.getenv('OPENCODE_API_KEY', '')}"
                        },
                    )
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    candidates.append(("claude (zen)", content, len(content)))
                    _bump("claude", "ok")
                else:
                    _bump("claude", "fail")
                    logger.warning(f"Claude/Zen returned {r.status_code} for task {i}")
            except Exception as e:
                logger.warning(f"Claude/Zen failed for task {i}: {e}")
                _bump("claude", "fail")

            # Pick longest as best
            if candidates:
                candidates.sort(key=lambda x: x[2], reverse=True)
                best_teacher, best_response, _ = candidates[0]
                examples.append({
                    "id": f"teacher_distill_{i}",
                    "category": cat,
                    "instruction": task,
                    "output": best_response,
                    "source_teacher": best_teacher,
                })
                logger.info(f"  Task {i}: teacher={best_teacher} ({len(candidates)} candidates)")

        with open(output_path, "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        return {
            "path": str(output_path),
            "examples": len(examples),
            "teacher_stats": teacher_stats,
        }

    # ── Peer learning (PC1 <-> PC2) ──────────────────────────────────

    async def run_peer_learning(
        self,
        tasks: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
    ) -> Dict:
        peer = getattr(self.owner, "peer_chat", None)
        if peer is None:
            return {"error": "peer_chat not initialized"}
        tasks = tasks or DEFAULT_PEER_TASKS
        if not peer.pc1.online and not peer.pc2.online:
            await peer.ping()
        result = await peer.learn_from_best(tasks, categories)
        memory = getattr(self.owner, "hybrid_memory", None)
        if memory is not None:
            peer.post_report_to_memory(memory, "PeerChat Auto-Learning Session")
        return result

    async def run_peer_conversation(
        self,
        topic: Optional[str] = None,
        rounds: int = 2,
    ) -> List:
        peer = getattr(self.owner, "peer_chat", None)
        if peer is None:
            return []
        await peer.ping()
        history = await peer.peer_conversation(rounds=rounds, topic=topic)
        memory = getattr(self.owner, "hybrid_memory", None)
        if memory is not None:
            peer.post_report_to_memory(memory, f"PeerChat: {topic}")
        return history
