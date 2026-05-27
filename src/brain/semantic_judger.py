"""
SemanticJudger - LLM juzga conflictos de memoria

Patron extraido de Engram (Go):
Cuando una gema guarda una decision/recuerdo, el SemanticJudger:
1. Busca recuerdos similares en FTS5
2. Usa LLM local para juzgar si el nuevo recuerdo:
   - CONTRADICE un existente
   - SOBRESCRIBE uno obsoleto
   - COMPLEMENTA uno existente
   - ES NUEVO (sin conflicto)

Resuelve contradicciones entre gemas automaticamente.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
MEMORY_DB = BASE_DIR / "memory" / "nexus_memory.db"


class Judgment(Enum):
    """Veredicto del SemanticJudger"""
    NEW = "new"  # No hay conflicto, es nuevo
    CONTRADICTS = "contradicts"  # Contradice un existente
    OVERWRITES = "overwrites"  # Sobrescribe uno obsoleto
    COMPLEMENTS = "complements"  # Complementa uno existente
    DUPLICATE = "duplicate"  # Es duplicado exacto


@dataclass
class MemoryConflict:
    """Conflicto de memoria detectado"""
    new_content: str
    existing_content: str
    existing_id: int
    judgment: Judgment
    reasoning: str
    confidence: float  # 0.0 - 1.0


class SemanticJudger:
    """Juzga conflictos de memoria usando LLM local"""

    def __init__(self, db_path: Optional[str] = None, ollama_url: str = "http://localhost:11434"):
        self.db_path = Path(db_path) if db_path else MEMORY_DB
        self.ollama_url = ollama_url
        self._ensure_db()

    def _ensure_db(self):
        """Asegura que la tabla de memoria existe"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                agent TEXT,
                content TEXT,
                topic TEXT,
                embedding TEXT,
                status TEXT DEFAULT 'active'
            )
        """)
        conn.commit()
        conn.close()

    def judge(self, new_content: str, topic: str, agent: str = "unknown") -> Optional[MemoryConflict]:
        """Juzga si el nuevo contenido tiene conflicto con memoria existente"""
        # Buscar contenido similar
        similar = self._find_similar(new_content, topic)

        if not similar:
            # No hay contenido similar, es nuevo
            self._save_memory(new_content, topic, agent)
            return None

        # Juzgar con LLM local
        judgment, reasoning, confidence = self._llm_judge(new_content, similar[0])

        conflict = MemoryConflict(
            new_content=new_content,
            existing_content=similar[0][3],  # content column
            existing_id=similar[0][0],  # id column
            judgment=judgment,
            reasoning=reasoning,
            confidence=confidence,
        )

        # Resolver conflicto
        self._resolve_conflict(conflict)

        return conflict

    def _find_similar(self, content: str, topic: str) -> List[Tuple]:
        """Busca contenido similar usando FTS5"""
        if not self.db_path.exists():
            return []

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Busqueda FTS5 si existe
        try:
            cursor.execute("""
                SELECT id, timestamp, agent, content, topic
                FROM findings
                WHERE content MATCH ?
                AND status != 'archived'
                ORDER BY rank
                LIMIT 5
            """, (content[:100],))
            results = cursor.fetchall()
            if results:
                conn.close()
                return results
        except Exception:
            pass

        # Fallback: busqueda por topic
        cursor.execute("""
            SELECT id, timestamp, agent, content, topic
            FROM findings
            WHERE topic = ?
            AND status != 'archived'
            ORDER BY timestamp DESC
            LIMIT 3
        """, (topic,))
        results = cursor.fetchall()
        conn.close()
        return results

    def _llm_judge(self, new_content: str, existing: Tuple) -> Tuple[Judgment, str, float]:
        """Usa LLM local para juzgar el conflicto"""
        import httpx

        existing_content = existing[3]
        existing_topic = existing[4]

        prompt = f"""Eres un juez de memoria para un sistema de IA multi-agente.

EXISTENTE (topic: {existing_topic}):
{existing_content[:500]}

NUEVO:
{new_content[:500]}

Juzga la relacion entre el contenido existente y el nuevo.
Responde SOLO con JSON en este formato:
{{"judgment": "new|contradicts|overwrites|complements|duplicate", "reasoning": "explicacion breve", "confidence": 0.0-1.0}}

Reglas:
- "new": No hay relacion, es informacion completamente nueva
- "contradicts": El nuevo contradice directamente al existente
- "overwrites": El nuevo actualiza/corrige al existente (version mas reciente)
- "complements": El nuevo anade informacion compatible al existente
- "duplicate": Es esencialmente lo mismo que el existente"""

        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "qwen2.5:0.5b",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1,
                },
                timeout=30.0,
            )

            if response.status_code == 200:
                result = response.json().get("response", "")
                # Parsear JSON de la respuesta
                result = result.strip()
                if result.startswith("```"):
                    result = result.split("```")[1]
                    if result.startswith("json"):
                        result = result[4:]
                result = result.strip()

                parsed = json.loads(result)
                judgment = Judgment(parsed.get("judgment", "new"))
                reasoning = parsed.get("reasoning", "")
                confidence = float(parsed.get("confidence", 0.5))
                return judgment, reasoning, confidence
        except Exception as e:
            logger.warning(f"LLM judgment failed: {e}")

        # Fallback: heuristica simple
        if new_content.strip() == existing_content.strip():
            return Judgment.DUPLICATE, "Contenido identico", 0.95
        if len(new_content) > len(existing_content) * 0.8:
            return Judgment.COMPLEMENTS, "Contenido similar pero extendido", 0.6
        return Judgment.NEW, "No se puede determinar automaticamente", 0.3

    def _resolve_conflict(self, conflict: MemoryConflict):
        """Resuelve el conflicto segun el veredicto"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        if conflict.judgment == Judgment.CONTRADICTS:
            # Marcar existente como conflictivo, guardar nuevo
            cursor.execute(
                "UPDATE findings SET status = 'conflict' WHERE id = ?",
                (conflict.existing_id,)
            )
            self._save_memory_raw(cursor, conflict.new_content)
            logger.info(f"Conflicto resuelto: existente #{conflict.existing_id} marcado como conflictivo")

        elif conflict.judgment == Judgment.OVERWRITES:
            # Archivar existente, guardar nuevo
            cursor.execute(
                "UPDATE findings SET status = 'archived' WHERE id = ?",
                (conflict.existing_id,)
            )
            self._save_memory_raw(cursor, conflict.new_content)
            logger.info(f"Sobrescritura: existente #{conflict.existing_id} archivado")

        elif conflict.judgment == Judgment.COMPLEMENTS:
            # Guardar nuevo sin modificar existente
            self._save_memory_raw(cursor, conflict.new_content)
            logger.info("Complemento: nuevo contenido agregado junto al existente")

        elif conflict.judgment == Judgment.DUPLICATE:
            # No guardar duplicado
            logger.info("Duplicado detectado, no se guarda")

        elif conflict.judgment == Judgment.NEW:
            # Guardar como nuevo
            self._save_memory_raw(cursor, conflict.new_content)

        conn.commit()
        conn.close()

    def _save_memory(self, content: str, topic: str, agent: str):
        """Guarda memoria sin conflicto"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        self._save_memory_raw(cursor, content, topic, agent)
        conn.commit()
        conn.close()

    def _save_memory_raw(self, cursor, content: str, topic: str = None, agent: str = None):
        """Guarda memoria directamente"""
        from datetime import datetime
        cursor.execute(
            "INSERT INTO findings (timestamp, agent, content, topic) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), agent or "unknown", content, topic or "general")
        )


# Singleton global
semantic_judger = SemanticJudger()
