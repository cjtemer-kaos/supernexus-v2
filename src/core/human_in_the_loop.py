"""
HumanInTheLoop - Validación humana explícita para SuperNEXUS v2.0

Basado en el patrón #8 del curso de Google: "Human-in-the-Loop"

Permite:
- Aprobación humana antes de acciones críticas
- Revisión de resultados antes de aplicar
- Feedback loop para mejorar respuestas
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ActionRisk(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class HumanReview:
    """Solicitud de revisión humana"""
    id: str
    action: str
    description: str
    risk_level: ActionRisk
    proposed_solution: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = ""
    reviewed_at: str = ""
    reviewer_feedback: str = ""
    modifications: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class HumanInTheLoop:
    """
    Patrón Human-in-the-Loop: validación humana para acciones críticas.
    
    Uso:
        hitl = HumanInTheLoop()
        
        # Registrar acción que requiere aprobación
        review = await hitl.request_review(
            action="delete_database",
            description="Delete old records from production DB",
            risk_level=ActionRisk.CRITICAL,
            proposed_solution="DELETE FROM records WHERE date < '2025-01-01'"
        )
        
        # Esperar aprobación (en UI real, esto sería un callback)
        await hitl.wait_for_approval(review.id)
        
        if review.status == ApprovalStatus.APPROVED:
            # Ejecutar acción
            pass
    """
    
    def __init__(self, auto_approve_risk: ActionRisk = ActionRisk.LOW):
        self.reviews: Dict[str, HumanReview] = {}
        self.auto_approve_risk = auto_approve_risk
        self._approval_callbacks: List[Callable] = []
        self._approval_events: Dict[str, asyncio.Event] = {}
    
    def add_approval_callback(self, callback: Callable):
        """Agrega callback para notificar aprobaciones pendientes"""
        self._approval_callbacks.append(callback)
    
    async def request_review(
        self,
        action: str,
        description: str,
        risk_level: ActionRisk,
        proposed_solution: str,
    ) -> HumanReview:
        """Solicita revisión humana"""
        import hashlib
        review_id = hashlib.md5(f"{action}{datetime.now()}".encode()).hexdigest()[:12]
        
        review = HumanReview(
            id=review_id,
            action=action,
            description=description,
            risk_level=risk_level,
            proposed_solution=proposed_solution,
        )
        
        self.reviews[review_id] = review
        self._approval_events[review_id] = asyncio.Event()
        
        if risk_level.value <= self.auto_approve_risk.value:
            review.status = ApprovalStatus.APPROVED
            review.reviewed_at = datetime.now().isoformat()
            review.reviewer_feedback = "Auto-approved (low risk)"
            logger.info(f"Review auto-approved: {review_id}")
        else:
            logger.info(f"Review requested: {review_id} ({risk_level.value})")
            
            for callback in self._approval_callbacks:
                try:
                    await callback(review)
                except Exception as e:
                    logger.error(f"Approval callback error: {e}")
        
        return review
    
    async def approve(self, review_id: str, feedback: str = "") -> bool:
        """Aprueba revisión"""
        review = self.reviews.get(review_id)
        if not review:
            return False
        
        review.status = ApprovalStatus.APPROVED
        review.reviewed_at = datetime.now().isoformat()
        review.reviewer_feedback = feedback
        
        if review_id in self._approval_events:
            self._approval_events[review_id].set()
        
        logger.info(f"Review approved: {review_id}")
        return True
    
    async def reject(self, review_id: str, feedback: str = "") -> bool:
        """Rechaza revisión"""
        review = self.reviews.get(review_id)
        if not review:
            return False
        
        review.status = ApprovalStatus.REJECTED
        review.reviewed_at = datetime.now().isoformat()
        review.reviewer_feedback = feedback
        
        if review_id in self._approval_events:
            self._approval_events[review_id].set()
        
        logger.info(f"Review rejected: {review_id}")
        return True
    
    async def modify(self, review_id: str, modifications: str, feedback: str = "") -> bool:
        """Modifica y aprueba revisión"""
        review = self.reviews.get(review_id)
        if not review:
            return False
        
        review.status = ApprovalStatus.MODIFIED
        review.reviewed_at = datetime.now().isoformat()
        review.modifications = modifications
        review.reviewer_feedback = feedback
        
        if review_id in self._approval_events:
            self._approval_events[review_id].set()
        
        logger.info(f"Review modified: {review_id}")
        return True
    
    async def wait_for_approval(self, review_id: str, timeout: float = 300.0) -> ApprovalStatus:
        """Espera aprobación (con timeout)"""
        event = self._approval_events.get(review_id)
        if not event:
            return ApprovalStatus.REJECTED
        
        review = self.reviews.get(review_id)
        if review and review.status != ApprovalStatus.PENDING:
            return review.status
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Approval timeout: {review_id}")
            review.status = ApprovalStatus.REJECTED
            review.reviewer_feedback = "Timeout: no response"
        
        return review.status
    
    def get_pending_reviews(self) -> List[HumanReview]:
        """Obtiene revisiones pendientes"""
        return [
            r for r in self.reviews.values()
            if r.status == ApprovalStatus.PENDING
        ]
    
    def get_review_history(self, limit: int = 20) -> List[Dict]:
        """Obtiene historial de revisiones"""
        sorted_reviews = sorted(
            self.reviews.values(),
            key=lambda r: r.created_at,
            reverse=True,
        )
        
        return [
            {
                "id": r.id,
                "action": r.action,
                "description": r.description,
                "risk_level": r.risk_level.value,
                "status": r.status.value,
                "created_at": r.created_at,
                "reviewed_at": r.reviewed_at,
                "feedback": r.reviewer_feedback,
            }
            for r in sorted_reviews[:limit]
        ]
    
    def should_require_approval(self, action: str, risk_level: ActionRisk) -> bool:
        """Verifica si acción requiere aprobación"""
        return risk_level.value > self.auto_approve_risk.value
    
    def get_status(self) -> Dict:
        return {
            "total_reviews": len(self.reviews),
            "pending_reviews": len(self.get_pending_reviews()),
            "auto_approve_risk": self.auto_approve_risk.value,
            "recent_reviews": self.get_review_history(5),
        }
