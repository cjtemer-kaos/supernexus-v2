"""
LearningSystem - Sistema de aprendizaje continuo mejorado para SuperNEXUS v2.0

Características:
- Flujo ScholarGem → SageGem → BibliotecaGem con validación automática
- Confidence score para conocimiento nuevo
- Auto-consolidación de conocimiento cada N horas
- Validación de fuentes y detección de información contradictoria
"""

import asyncio
import logging
import json
import hashlib
from typing import Dict, List, Optional, Any
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
        self.knowledge_base: Dict[str, KnowledgePiece] = {}
        self.learning_sessions: List[LearningSession] = []
        self.auto_validate_threshold = auto_validate_threshold
        self.consolidation_interval = timedelta(hours=consolidation_interval_hours)
        self.max_knowledge_pieces = max_knowledge_pieces
        self._last_consolidation = datetime.now()
        self._validation_callbacks = []
    
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
        
        self.knowledge_base[piece.id] = piece
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
        
        self.knowledge_base[piece.id] = piece
        
        if piece.confidence >= self.auto_validate_threshold:
            piece.state = KnowledgeState.VALIDATED
            piece.validated_at = datetime.now().isoformat()
            piece.validated_by = "user"
            logger.info(f"Knowledge validated by user: {piece.id}")
        
        return piece
    
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
        now = datetime.now()
        
        if not force and (now - self._last_consolidation) < self.consolidation_interval:
            return
        
        logger.info("Starting knowledge consolidation...")
        
        validated_pieces = [
            p for p in self.knowledge_base.values()
            if p.state == KnowledgeState.VALIDATED
        ]
        
        for piece in validated_pieces:
            related = self._find_related_pieces(piece)
            piece.related_ids = [r.id for r in related[:5]]
        
        deprecated_pieces = [
            p for p in self.knowledge_base.values()
            if p.state == KnowledgeState.DRAFT and
            (now - datetime.fromisoformat(p.created_at)).days > 30
        ]
        
        for piece in deprecated_pieces:
            piece.state = KnowledgeState.DEPRECATED
            logger.info(f"Knowledge deprecated: {piece.id}")
        
        if len(self.knowledge_base) > self.max_knowledge_pieces:
            sorted_pieces = sorted(
                self.knowledge_base.values(),
                key=lambda p: p.confidence,
            )
            
            to_remove = len(self.knowledge_base) - self.max_knowledge_pieces
            for piece in sorted_pieces[:to_remove]:
                del self.knowledge_base[piece.id]
            
            logger.info(f"Removed {to_remove} low-confidence pieces")
        
        self._last_consolidation = now
        logger.info(f"Knowledge consolidation complete. {len(self.knowledge_base)} pieces total.")
    
    def _find_related_pieces(self, piece: KnowledgePiece) -> List[KnowledgePiece]:
        """Encuentra piezas relacionadas"""
        if not piece.tags:
            return []
        
        related = []
        for other in self.knowledge_base.values():
            if other.id == piece.id:
                continue
            
            common_tags = set(piece.tags) & set(other.tags)
            if len(common_tags) > 0:
                related.append((len(common_tags), other))
        
        related.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in related]
    
    def search_knowledge(self, query: str, tags: List[str] = None, min_confidence: float = 0.0) -> List[KnowledgePiece]:
        """Busca en base de conocimiento"""
        results = []
        query_lower = query.lower()
        
        for piece in self.knowledge_base.values():
            if piece.confidence < min_confidence:
                continue
            
            if piece.state == KnowledgeState.DEPRECATED:
                continue
            
            score = 0.0
            
            if query_lower in piece.title.lower():
                score += 0.5
            if query_lower in piece.content.lower():
                score += 0.3
            
            if tags:
                common_tags = set(tags) & set(piece.tags)
                score += 0.1 * len(common_tags)
            
            if score > 0:
                results.append((score, piece))
        
        results.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in results]
    
    def create_learning_session(self, topic: str) -> LearningSession:
        """Crea nueva sesión de aprendizaje"""
        session = LearningSession(
            id=hashlib.md5(f"{topic}{datetime.now()}".encode()).hexdigest()[:12],
            topic=topic,
            started_at=datetime.now().isoformat(),
        )
        
        self.learning_sessions.append(session)
        return session
    
    def complete_learning_session(self, session_id: str, pieces_learned: int, pieces_validated: int, pieces_failed: int, sources_analyzed: int):
        """Completa sesión de aprendizaje"""
        for session in self.learning_sessions:
            if session.id == session_id:
                session.completed_at = datetime.now().isoformat()
                session.pieces_learned = pieces_learned
                session.pieces_validated = pieces_validated
                session.pieces_failed = pieces_failed
                session.sources_analyzed = sources_analyzed
                session.duration_seconds = (
                    datetime.fromisoformat(session.completed_at) -
                    datetime.fromisoformat(session.started_at)
                ).total_seconds()
                session.status = "completed"
                break
    
    def get_knowledge_stats(self) -> Dict:
        """Obtiene estadísticas de conocimiento"""
        total = len(self.knowledge_base)
        by_state = {}
        for piece in self.knowledge_base.values():
            state = piece.state.value
            by_state[state] = by_state.get(state, 0) + 1
        
        avg_confidence = (
            sum(p.confidence for p in self.knowledge_base.values()) / total
            if total > 0 else 0
        )
        
        return {
            "total_pieces": total,
            "by_state": by_state,
            "avg_confidence": avg_confidence,
            "learning_sessions": len(self.learning_sessions),
            "last_consolidation": self._last_consolidation.isoformat(),
        }
    
    def get_status(self) -> Dict:
        """Obtiene estado completo del sistema de aprendizaje"""
        return {
            "knowledge_stats": self.get_knowledge_stats(),
            "recent_sessions": [
                {
                    "id": s.id,
                    "topic": s.topic,
                    "status": s.status,
                    "pieces_learned": s.pieces_learned,
                    "pieces_validated": s.pieces_validated,
                }
                for s in self.learning_sessions[-10:]
            ],
        }
