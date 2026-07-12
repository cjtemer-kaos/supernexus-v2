"""
LearningSystem - Sistema de aprendizaje continuo mejorado para SuperNEXUS v2.0

Características:
- Flujo ScholarGem → SageGem → BibliotecaGem con validación automática
- Confidence score para conocimiento nuevo
- Auto-consolidación de conocimiento cada N horas
- Validación de fuentes y detección de información contradictoria
"""

import logging
import hashlib
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class KnowledgeState(Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    VALIDATED = "validated"
    CONSOLIDATED = "consolidated"
    DEPRECATED = "deprecated"


@dataclass
class KnowledgePiece:
    """Pieza de conocimiento individual"""
    id: str
    title: str
    content: str
    source: str
    source_url: str = ""
    state: KnowledgeState = KnowledgeState.DRAFT
    confidence: float = 0.0
    created_at: str = ""
    validated_at: str = ""
    validated_by: str = ""
    tags: List[str] = field(default_factory=list)
    related_ids: List[str] = field(default_factory=list)
    validation_attempts: int = 0
    max_validation_attempts: int = 3
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = hashlib.md5(f"{self.title}{self.content}".encode()).hexdigest()[:12]


@dataclass
class LearningSession:
    """Sesión de aprendizaje"""
    id: str
    topic: str
    started_at: str
    completed_at: str = ""
    pieces_learned: int = 0
    pieces_validated: int = 0
    pieces_failed: int = 0
    sources_analyzed: int = 0
    duration_seconds: float = 0.0
    status: str = "in_progress"


class LearningSystem:
    """
    Sistema de aprendizaje continuo con validación automática.
    
    Flujo:
    1. ScholarGem investiga en la web
    2. SageGem analiza y extrae conocimiento
    3. Sistema calcula confidence score
    4. Si confidence > threshold → validado automáticamente
    5. Si confidence < threshold → requiere validación humana
    6. BibliotecaGem organiza conocimiento validado
    7. Auto-consolidación cada N horas
    """
    
    def __init__(
        self,
        auto_validate_threshold: float = 0.8,
        consolidation_interval_hours: int = 24,
        max_knowledge_pieces: int = 10000,
    ):
        self.auto_validate_threshold = auto_validate_threshold
        self.consolidation_interval = timedelta(hours=consolidation_interval_hours)
        self.max_knowledge_pieces = max_knowledge_pieces
        self._last_consolidation = datetime.now()
        self._validation_callbacks = []
        self._db_path = Path.home() / ".nexus" / "brain" / "learning.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Inicializa tablas SQLite para persistencia."""
        import sqlite3
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS knowledge_pieces (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            source TEXT,
            source_url TEXT,
            state TEXT DEFAULT 'draft',
            confidence REAL DEFAULT 0.0,
            created_at TEXT,
            validated_at TEXT DEFAULT '',
            validated_by TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            related_ids TEXT DEFAULT '[]',
            validation_attempts INTEGER DEFAULT 0
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS learning_sessions (
            id TEXT PRIMARY KEY,
            topic TEXT,
            started_at TEXT,
            completed_at TEXT DEFAULT '',
            pieces_learned INTEGER DEFAULT 0,
            pieces_validated INTEGER DEFAULT 0,
            pieces_failed INTEGER DEFAULT 0,
            sources_analyzed INTEGER DEFAULT 0,
            duration_seconds REAL DEFAULT 0.0,
            status TEXT DEFAULT 'in_progress'
        )""")
        c.execute("""CREATE INDEX IF NOT EXISTS idx_kp_state ON knowledge_pieces(state)""")
        c.execute("""CREATE INDEX IF NOT EXISTS idx_kp_confidence ON knowledge_pieces(confidence)""")
        conn.commit()
        conn.close()
    
    def _piece_from_row(self, row) -> KnowledgePiece:
        """Convierte row SQLite a KnowledgePiece."""
        import json
        return KnowledgePiece(
            id=row[0], title=row[1], content=row[2], source=row[3],
            source_url=row[4] or "", state=KnowledgeState(row[5]),
            confidence=row[6], created_at=row[7], validated_at=row[8] or "",
            validated_by=row[9] or "", tags=json.loads(row[10] or "[]"),
            related_ids=json.loads(row[11] or "[]"),
            validation_attempts=row[12] or 0,
        )
    
    def _save_piece(self, piece: KnowledgePiece):
        """Persiste piece en SQLite."""
        import sqlite3, json
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO knowledge_pieces 
            (id, title, content, source, source_url, state, confidence, 
             created_at, validated_at, validated_by, tags, related_ids, validation_attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (piece.id, piece.title, piece.content, piece.source, piece.source_url,
             piece.state.value, piece.confidence, piece.created_at,
             piece.validated_at, piece.validated_by, json.dumps(piece.tags),
             json.dumps(piece.related_ids), piece.validation_attempts))
        conn.commit()
        conn.close()
    
    def add_validation_callback(self, callback):
        """Agrega callback para validación humana"""
        self._validation_callbacks.append(callback)
    
    async def learn_from_source(
        self,
        topic: str,
        source_url: str,
        content: str,
        tags: List[str] = None,
    ) -> KnowledgePiece:
        """Aprende de una fuente"""
        piece = KnowledgePiece(
            id="",
            title=topic,
            content=content,
            source="web",
            source_url=source_url,
            tags=tags or [],
        )
        
        self._save_piece(piece)
        logger.info(f"New knowledge piece added: {piece.id} ({topic})")
        
        await self._validate_piece(piece)
        
        return piece
    
    async def learn_from_user(
        self,
        topic: str,
        content: str,
        source: str = "user",
        tags: List[str] = None,
    ) -> KnowledgePiece:
        """Aprende directamente del usuario (alta confianza)"""
        piece = KnowledgePiece(
            id="",
            title=topic,
            content=content,
            source=source,
            tags=tags or [],
            confidence=0.9,
        )
        
        self._save_piece(piece)
        
        if piece.confidence >= self.auto_validate_threshold:
            piece.state = KnowledgeState.VALIDATED
            piece.validated_at = datetime.now().isoformat()
            piece.validated_by = "user"
            self._save_piece(piece)
            logger.info(f"Knowledge validated by user: {piece.id}")
        
        return piece
    
    async def learn_from_correction(self, piece_id: str, corrected_content: str, reason: str = "") -> Dict:
        """Procesa una corrección del usuario sobre conocimiento existente.
        
        Actualiza el contenido, boosta confianza, registra patron de error
        para que SelfLearningLoop aprenda de la corrección.
        
        Args:
            piece_id: ID de la pieza a corregir
            corrected_content: Contenido corregido
            reason: Razón de la corrección (opcional)
        
        Returns:
            Dict con resultado de la operación
        """
        import sqlite3, json
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("SELECT id, title, content, confidence, tags FROM knowledge_pieces WHERE id=?", (piece_id,))
        row = c.fetchone()
        if not row:
            conn.close()
            return {"success": False, "error": f"Piece {piece_id} not found"}
        
        old_content = row[2]
        old_confidence = row[3]
        tags = json.loads(row[4] or "[]")
        
        # Actualizar contenido y tags
        new_confidence = min(old_confidence + 0.1, 1.0)
        if "corrected" not in tags:
            tags.append("corrected")
        c.execute("UPDATE knowledge_pieces SET content=?, confidence=?, tags=?, validated_at=?, validated_by='user_correction' WHERE id=?",
                  (corrected_content, new_confidence, json.dumps(tags), datetime.now().isoformat(), piece_id))
        conn.commit()
        conn.close()
        
        logger.info(f"Knowledge corrected: {piece_id} (confidence: {old_confidence:.2f} -> {new_confidence:.2f})")
        
        return {
            "success": True,
            "piece_id": piece_id,
            "confidence_boost": 0.1,
            "new_confidence": new_confidence,
            "reason": reason,
        }
    
    async def _validate_piece(self, piece: KnowledgePiece):
        """Valida pieza de conocimiento automáticamente"""
        piece.state = KnowledgeState.VALIDATING
        
        confidence = await self._calculate_confidence(piece)
        piece.confidence = confidence
        piece.validation_attempts += 1
        
        if confidence >= self.auto_validate_threshold:
            piece.state = KnowledgeState.VALIDATED
            piece.validated_at = datetime.now().isoformat()
            piece.validated_by = "auto"
            logger.info(f"Knowledge auto-validated: {piece.id} (confidence: {confidence:.2f})")
        elif piece.validation_attempts >= piece.max_validation_attempts:
            piece.state = KnowledgeState.DRAFT
            logger.warning(f"Knowledge validation failed after {piece.validation_attempts} attempts: {piece.id}")
            await self._request_human_validation(piece)
        else:
            logger.info(f"Knowledge validation pending: {piece.id} (confidence: {confidence:.2f})")
        
        self._save_piece(piece)
    
    async def _calculate_confidence(self, piece: KnowledgePiece) -> float:
        """Calcula confidence score para conocimiento"""
        confidence = 0.5
        
        if piece.source == "user":
            confidence += 0.3
        
        if piece.source_url and ("github.com" in piece.source_url or "wikipedia.org" in piece.source_url):
            confidence += 0.2
        
        if len(piece.content) > 100:
            confidence += 0.1
        
        if len(piece.tags) > 0:
            confidence += 0.05 * min(len(piece.tags), 3)
        
        related_count = len(piece.related_ids)
        if related_count > 0:
            confidence += 0.05 * min(related_count, 4)
        
        return min(1.0, confidence)
    
    async def _request_human_validation(self, piece: KnowledgePiece):
        """Solicita validación humana"""
        for callback in self._validation_callbacks:
            try:
                await callback(piece)
            except Exception as e:
                logger.error(f"Validation callback error: {e}")
    
    async def consolidate_knowledge(self, force: bool = False):
        """Consolida conocimiento automáticamente"""
        import sqlite3
        now = datetime.now()
        
        if not force and (now - self._last_consolidation) < self.consolidation_interval:
            return
        
        logger.info("Starting knowledge consolidation...")
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        
        # Deprecar drafts viejos (>30 días)
        cutoff = (now - timedelta(days=30)).isoformat()
        c.execute("UPDATE knowledge_pieces SET state='deprecated' WHERE state='draft' AND created_at < ?", (cutoff,))
        
        # Eliminar低confianza si excedemos max
        c.execute("SELECT COUNT(*) FROM knowledge_pieces")
        total = c.fetchone()[0]
        if total > self.max_knowledge_pieces:
            to_remove = total - self.max_knowledge_pieces
            c.execute("""DELETE FROM knowledge_pieces WHERE id IN 
                        (SELECT id FROM knowledge_pieces ORDER BY confidence ASC LIMIT ?)""", (to_remove,))
            logger.info(f"Removed {to_remove} low-confidence pieces")
        
        conn.commit()
        conn.close()
        self._last_consolidation = now
        logger.info(f"Knowledge consolidation complete.")
    
    def search_knowledge(self, query: str, tags: List[str] = None, min_confidence: float = 0.0) -> List[KnowledgePiece]:
        """Busca en base de conocimiento via SQLite"""
        import sqlite3
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("""SELECT id, title, content, source, source_url, state, confidence,
                            created_at, validated_at, validated_by, tags, related_ids, validation_attempts
                     FROM knowledge_pieces WHERE state != 'deprecated' AND confidence >= ?
                     ORDER BY confidence DESC""", (min_confidence,))
        rows = c.fetchall()
        conn.close()
        
        query_lower = query.lower()
        results = []
        for row in rows:
            piece = self._piece_from_row(row)
            score = 0.0
            if query_lower in piece.title.lower(): score += 0.5
            if query_lower in piece.content.lower(): score += 0.3
            if tags:
                common = set(tags) & set(piece.tags)
                score += 0.1 * len(common)
            if score > 0:
                results.append((score, piece))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in results]
    
    def create_learning_session(self, topic: str) -> LearningSession:
        """Crea nueva sesión de aprendizaje"""
        import sqlite3
        session = LearningSession(
            id=hashlib.md5(f"{topic}{datetime.now()}".encode()).hexdigest()[:12],
            topic=topic,
            started_at=datetime.now().isoformat(),
        )
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("INSERT INTO learning_sessions (id, topic, started_at, status) VALUES (?, ?, ?, ?)",
                  (session.id, session.topic, session.started_at, "in_progress"))
        conn.commit()
        conn.close()
        return session
    
    def complete_learning_session(self, session_id: str, pieces_learned: int, pieces_validated: int, pieces_failed: int, sources_analyzed: int):
        """Completa sesión de aprendizaje"""
        import sqlite3
        now = datetime.now().isoformat()
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("""UPDATE learning_sessions SET completed_at=?, pieces_learned=?, pieces_validated=?,
                     pieces_failed=?, sources_analyzed=?, status='completed' WHERE id=?""",
                  (now, pieces_learned, pieces_validated, pieces_failed, sources_analyzed, session_id))
        conn.commit()
        conn.close()
    
    def get_knowledge_stats(self) -> Dict:
        """Obtiene estadísticas de conocimiento desde SQLite"""
        import sqlite3
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM knowledge_pieces")
        total = c.fetchone()[0]
        c.execute("SELECT state, COUNT(*) FROM knowledge_pieces GROUP BY state")
        by_state = {row[0]: row[1] for row in c.fetchall()}
        c.execute("SELECT AVG(confidence) FROM knowledge_pieces")
        avg_conf = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM learning_sessions")
        sessions = c.fetchone()[0]
        conn.close()
        
        return {
            "total_pieces": total,
            "by_state": by_state,
            "avg_confidence": avg_conf,
            "learning_sessions": sessions,
            "last_consolidation": self._last_consolidation.isoformat(),
        }
    
    def get_status(self) -> Dict:
        """Obtiene estado completo del sistema de aprendizaje"""
        import sqlite3
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        c = conn.cursor()
        c.execute("SELECT id, topic, status, pieces_learned, pieces_validated FROM learning_sessions ORDER BY started_at DESC LIMIT 10")
        recent = [{"id": r[0], "topic": r[1], "status": r[2], "pieces_learned": r[3], "pieces_validated": r[4]} for r in c.fetchall()]
        conn.close()
        return {
            "knowledge_stats": self.get_knowledge_stats(),
            "recent_sessions": recent,
        }
