"""Brain: Memory — gestion de memoria de sesion del Director.

Tres operaciones:
    1. get_memory_context() — recupera memorias relevantes del consolidator
       para inyectarlas como contexto inline en cada llamada al LLM.
    2. recover_session_context() — al arrancar, lee el contexto de la sesion
       previa y lo persiste para que MCP bridge lo levante.
    3. persist_session_state() — guarda estado de sesion periodicamente.

Design:
    MemoryBrain recibe el director como owner y lee:
        - owner.memory_consolidator  — para get_memory_context
        - owner.context_recovery     — para recover y persist
    Degrada gracefully con string vacio o log de error.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# Default config
DEFAULT_MEMORY_LIMIT: int = 5
DEFAULT_FACT_MAX_LEN: int = 200
DEFAULT_FACT_MIN_LEN: int = 10
NEXUS_BRAIN_DIR: Path = Path(os.environ.get("NEXUS_BRAIN", str(Path.home() / ".nexus" / "brain")))


class MemoryBrain:
    """Gestor de memoria del Director — recuperacion + persistencia de sesion."""

    def __init__(self, owner: Any):
        """
        Args:
            owner: el Director — espera owner.memory_consolidator (para
                get_memory_context) y owner.context_recovery (para session ops).
                Ambos opcionales: degrada con string vacio o log de error.
        """
        self.owner = owner

    # ── Memory injection (per-call context) ─────────────────────────────

    def get_memory_context(
        self,
        task: str,
        limit: int = DEFAULT_MEMORY_LIMIT,
    ) -> str:
        """Recupera memorias relevantes del consolidator + cerebro conocimientos.

        Returns:
            String formateado para inyectar al prompt, o "" si no hay memorias
            o el consolidator no esta disponible.
        """
        lines = []
        # 1. Memory consolidator (conversation-extracted facts)
        consolidator = getattr(self.owner, "memory_consolidator", None)
        if consolidator:
            try:
                memories = consolidator.search(task, limit=limit)
                if memories:
                    lines.append("[De mi memoria de interacciones previas:]")
                    for m in memories:
                        fact = (m.get("fact") or "").strip()
                        topic = m.get("topic_key", "")
                        if fact and len(fact) > DEFAULT_FACT_MIN_LEN:
                            lines.append(f"- [{topic}] {fact[:DEFAULT_FACT_MAX_LEN]}")
            except Exception as e:
                logger.debug(f"get_memory_context consolidator failed: {e}")

        # 2. Cerebro conocimientos (stored knowledge from URLs, manual entries)
        try:
            from src.brain.cerebro import Cerebro
            from datetime import datetime, timezone
            import re
            cerebro = Cerebro()
            raw = re.sub(r'[^\w\s]', ' ', task)[:100]
            # Filter out short words and Spanish/English stop words
            _STOP = {"que","es","de","en","la","el","los","las","del","con","por","para","un","una",
                     "se","no","lo","su","al","como","mas","pero","sus","le","ya","este","esta",
                     "the","and","for","are","but","not","you","all","can","had","her","was",
                     "one","our","out","has","have","been","some","them","than","what","when",
                     "which","will","with","your"}
            words = [w.lower() for w in raw.split() if len(w) > 2 and w.lower() not in _STOP]
            conocimientos = cerebro.obtener_conocimientos()
            if conocimientos and words:
                matched = []
                now = datetime.now(timezone.utc)
                for c in conocimientos:
                    tema = (c.get("tema") or "").lower()
                    contenido = (c.get("contenido") or "").lower()
                    fuente = (c.get("fuente") or "").lower()
                    haystack = " ".join([tema, contenido, fuente])
                    if not any(w in haystack for w in words):
                        continue
                    # Relevance: matches in tema/fuente = 3x, in contenido = 1x
                    score = 0
                    for w in words:
                        if w in tema or w in fuente:
                            score += 3
                        elif w in contenido:
                            score += 1
                    # Recency boost: +2 if updated in last 7 days
                    fecha_str = c.get("fecha")
                    if fecha_str:
                        try:
                            f = datetime.fromisoformat(fecha_str)
                            if f.tzinfo is None:
                                f = f.replace(tzinfo=timezone.utc)
                            days_old = (now - f).days
                            if days_old < 7:
                                score += 2
                            elif days_old < 30:
                                score += 1
                        except Exception:
                            pass
                    # Reliability boost: +1 per 5 revisions
                    revisado = c.get("veces_revisado") or 0
                    score += revisado // 5
                    matched.append((score, c))

                matched.sort(key=lambda x: (x[0], x[1].get("utilidad", 0)), reverse=True)
                if matched:
                    import re as _re
                    lines.append("\n[Conocimiento que has estudiado:]")
                    budget = 3000
                    for _, c in matched:
                        tema = c.get("tema", "")[:60]
                        fuente = c.get("fuente", "") or ""
                        raw = (c.get("contenido") or "")[:1500]
                        clean = _re.sub(r'<[^>]+>', '', raw).replace("\n", " ").strip()
                        fecha = (c.get("fecha") or "")[:10]
                        util = c.get("utilidad", 5)
                        entry = f"- {tema}"
                        if fuente:
                            entry += f" | {fuente}"
                        if fecha:
                            entry += f" ({fecha})"
                        entry += f" ★{util}: {clean}"
                        if len(entry) > budget:
                            break
                        lines.append(entry)
                        budget -= len(entry)
        except Exception as e:
            import traceback
            logger.debug(f"get_memory_context cerebro failed: {e}\n{traceback.format_exc()}")

        # 3. Episodic memory: past conversations matching the task
        try:
            from src.brain.cerebro import Cerebro as _C
            import re as _re
            _c = _C()
            _raw = _re.sub(r'[^\w\s]', ' ', task)[:100]
            _STOP2 = {"que","es","de","en","la","el","los","las","del","con","por","para","un","una",
                      "se","no","lo","su","al","como","mas","pero","sus","le","ya","este","esta",
                      "the","and","for","are","but","not","you","all","can","had","her","was",
                      "one","our","out","has","have","been","some","them","than","what","when",
                      "which","will","with","your"}
            _words = [w.lower() for w in _raw.split() if len(w) > 2 and w.lower() not in _STOP2]
            if _words:
                _conn = sqlite3.connect(str(Path.home() / ".nexus" / "brain" / "cerebro.db"), timeout=10)
                _cur = _conn.cursor()
                _cur.execute("SELECT fecha, gem, mensaje, respuesta FROM conversaciones ORDER BY id DESC LIMIT 200")
                _episodic = []
                for row in _cur.fetchall():
                    _text = f"{row[2]} {row[3]}"
                    _txt_lower = _text.lower()
                    if any(w in _txt_lower for w in _words):
                        _episodic.append(row)
                _conn.close()
                if _episodic:
                    lines.append("\n[Conversaciones previas relacionadas:]")
                    _budget = 800
                    for _fecha, _gem, _msg, _resp in _episodic[:10]:
                        if not _resp or len(_resp.strip()) < 5:
                            continue
                        _entry = f"- ({_fecha[:10]}) [{_gem}] {_msg[:100]}: {_resp[:150]}".replace("\n", " ")
                        if len(_entry) > _budget:
                            break
                        lines.append(_entry)
                        _budget -= len(_entry)
        except Exception as e:
            logger.debug(f"get_memory_context conversaciones failed: {e}")

        return "\n".join(lines) if len(lines) > 1 else ""

    # ── Hippocampus: cross-source associative recall ────────────────────

    def hippocampus_recall(
        self,
        task: str,
        limit: int = 5,
        sources: List[str] | None = None,
        format: str = "block",
    ) -> str:
        """Lethe-style associative recall across ALL memory backends.

        Unlike `get_memory_context` (consolidator-only), this fan-outs to
        every available source, merges hits, dedupes by content prefix,
        and returns a single formatted block ready to inject as system
        addition.

        Args:
            task: query text — drives semantic + keyword search.
            limit: max hits per source.
            sources: subset to query — None means all available:
                     'consolidator', 'observations', 'cerebro'.
            format: 'block' (multi-line inline block) or 'json' (raw list).

        Returns:
            Markdown-formatted block (empty string if nothing found OR if
            the task is too short / too generic to be useful). Never raises.
        """
        if not task or len(task.strip()) < 4:
            return ""
        # Strip filler that confuses keyword/semantic search.
        q = task.strip()[:200]

        wanted = set(sources or ("consolidator", "observations", "cerebro"))
        hits: List[Dict[str, Any]] = []

        # 1) Consolidator (existing path — facts + topics)
        if "consolidator" in wanted:
            try:
                cons = getattr(self.owner, "memory_consolidator", None)
                if cons is not None:
                    for m in (cons.search(q, limit=limit) or []):
                        fact = (m.get("fact") or "").strip()
                        if fact:
                            hits.append({
                                "source": "consolidator",
                                "text": fact,
                                "tag": m.get("topic_key", ""),
                            })
            except Exception as e:
                logger.debug(f"hippocampus: consolidator failed: {e}")

        # 2) Observations DB (nexus_memory.db) via mcp_bridge_server in-process
        if "observations" in wanted:
            try:
                # Lazy import to avoid pulling FastMCP at every chat.
                import asyncio
                from src.bridges import mcp_bridge_server as _mbs
                # search_observations is async — synchronous call requires loop.
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None
                if loop and loop.is_running():
                    # We're inside an async caller; skip to avoid nested-loop hell.
                    # Callers in an event loop should use the async sister method.
                    pass
                else:
                    raw = asyncio.run(_mbs.search_observations(query=q, limit=limit))
                    obs = json.loads(raw).get("results", []) if raw else []
                    for o in obs:
                        text = (o.get("content") or "").strip()
                        if text:
                            hits.append({
                                "source": "observations",
                                "text": text[:300],
                                "tag": f"obs#{o.get('id')} cat={o.get('category')}",
                            })
            except Exception as e:
                logger.debug(f"hippocampus: observations failed: {e}")

        # 3) Cerebro brain_recall (cerebro.db) if available on the director
        if "cerebro" in wanted:
            try:
                cerebro = getattr(self.owner, "cerebro", None)
                if cerebro is not None and hasattr(cerebro, "recall"):
                    for r in (cerebro.recall(q, limit=limit) or []):
                        text = (r.get("content") or r.get("text") or "").strip()
                        if text:
                            hits.append({
                                "source": "cerebro",
                                "text": text[:300],
                                "tag": r.get("topic", "") or r.get("category", ""),
                            })
            except Exception as e:
                logger.debug(f"hippocampus: cerebro failed: {e}")

        # Dedupe by content prefix (first 80 chars normalized).
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for h in hits:
            key = " ".join(h["text"][:80].lower().split())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(h)
            if len(deduped) >= limit * 2:
                break

        # Salience rerank — emotionally tagged memories surface higher
        # (commit 41). Opt-out via env if deterministic order needed.
        if deduped and not os.environ.get("NEXUS_SALIENCE_DISABLED"):
            try:
                from src.brain.salience import salience
                # Use tag as the entry_id key (consolidator/observation already
                # carries the tag/topic in the merged dict).
                deduped = salience.rerank(
                    deduped, key=lambda h: h.get("tag", "")[:32] or "?",
                    salience_weight=0.4,
                )
            except Exception:
                pass

        if not deduped:
            return ""
        if format == "json":
            return json.dumps(deduped, ensure_ascii=False)
        # Default: human-readable block for prompt injection.
        lines = [
            "[Hippocampus recall — relevant memories from past sessions:]",
        ]
        for h in deduped:
            tag = f" [{h['tag']}]" if h.get("tag") else ""
            lines.append(f"- ({h['source']}){tag} {h['text']}")
        return "\n".join(lines)

    # ── Session lifecycle ───────────────────────────────────────────────

    def recover_session_context(self, project: str) -> Dict[str, Any]:
        """Levanta contexto de sesion previa, lo guarda a JSON para MCP bridge.

        Returns:
            Dict con el contexto (o vacio si no hay context_recovery / fallo).
        """
        recovery = getattr(self.owner, "context_recovery", None)
        if recovery is None:
            return {}
        try:
            context = recovery.build_session_context(project)
            if context.get("context_summary"):
                NEXUS_BRAIN_DIR.mkdir(parents=True, exist_ok=True)
                context_file = NEXUS_BRAIN_DIR / "recovered_context.json"
                with open(context_file, "w", encoding="utf-8") as f:
                    json.dump(context, f, indent=2, ensure_ascii=False)
                logger.info(f"Session context recovered and saved to {context_file}")
            return context
        except Exception as e:
            logger.error(f"Failed to recover session context: {e}")
            return {}

    def persist_session_state(
        self,
        session_id: str,
        project: str,
        messages: List[Dict],
        tokens: int = 0,
    ) -> bool:
        """Persistir estado de sesion (llamar periodicamente o al finalizar).

        Returns:
            True si persistio OK, False si fallo o no hay context_recovery.
        """
        recovery = getattr(self.owner, "context_recovery", None)
        if recovery is None:
            return False

        # Late import to avoid circular dependency at module load
        try:
            from src.core.session_context_recovery import SessionState
        except Exception as e:
            logger.warning(f"SessionState import failed: {e}")
            return False

        try:
            max_recent = getattr(recovery, "max_recent_messages", 20)
            state = SessionState(
                session_id=session_id,
                project=project,
                started_at=datetime.now().isoformat(),
                last_activity=datetime.now().isoformat(),
                message_count=len(messages),
                total_tokens=tokens,
                recent_messages=messages[-max_recent:],
            )
            recovery.save_session_state(state)
            return True
        except Exception as e:
            logger.error(f"Failed to persist session state: {e}")
            return False
