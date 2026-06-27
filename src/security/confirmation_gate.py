"""
confirmation_gate — HITL approval for destructive operations.

Pattern (openakita): never auto-execute destructive ops without explicit
confirmation. Each request gets a token; user POSTs the token back to
approve. Auto-expire after TTL.

Default destructive ops:
    memory.hard_delete    delete_observation hard=True
    memory.purge_archived hard_purge_archived
    gemas.import_signed   .nexus-gema with sig (operator must trust key)
    setup.reset           wipe wizard state
    ofp.send              send to remote peer

Opt-out: NEXUS_CONFIRM_DISABLED=1 (single-user trusted environments).
"""
from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)

PENDING_TTL_S = 300  # 5 min


@dataclass
class PendingOp:
    token: str
    op: str
    payload: dict
    requested_at: float
    expires_at: float
    approved: bool = False
    rejected: bool = False


class ConfirmationGate:
    def __init__(self):
        self._pending: Dict[str, PendingOp] = {}
        self._lock = threading.Lock()

    @staticmethod
    def disabled() -> bool:
        return os.environ.get("NEXUS_CONFIRM_DISABLED", "0") == "1"

    def request(self, op: str, payload: Optional[dict] = None) -> Dict:
        """Issue a confirmation token. Returns {token, expires_at, op}."""
        if self.disabled():
            return {"ok": True, "auto_approved": True, "op": op}
        token = secrets.token_urlsafe(16)
        now = time.time()
        po = PendingOp(token=token, op=op, payload=payload or {},
                       requested_at=now, expires_at=now + PENDING_TTL_S)
        with self._lock:
            self._pending[token] = po
            # GC expired
            for k in [k for k, p in self._pending.items() if p.expires_at < now]:
                self._pending.pop(k, None)
        return {"ok": True, "token": token, "op": op,
                "expires_in_s": PENDING_TTL_S,
                "instructions": "POST /api/confirm with body: {token, approve: true|false}"}

    def respond(self, token: str, approve: bool) -> Dict:
        with self._lock:
            po = self._pending.get(token)
            if po is None:
                return {"ok": False, "error": "unknown or expired token"}
            if time.time() > po.expires_at:
                self._pending.pop(token, None)
                return {"ok": False, "error": "token expired"}
            po.approved = approve
            po.rejected = not approve
        return {"ok": True, "approved": approve, "op": po.op}

    def consume(self, token: str) -> bool:
        """Caller checks: was this token approved? If yes, removes + returns True.
        Returns False if missing/expired/not-approved."""
        if self.disabled():
            return True
        with self._lock:
            po = self._pending.pop(token, None)
            if po is None or time.time() > po.expires_at:
                return False
            return po.approved

    def pending_list(self) -> list:
        with self._lock:
            now = time.time()
            return [
                {"op": p.op, "requested_at": p.requested_at,
                 "expires_in_s": max(0, int(p.expires_at - now))}
                for p in self._pending.values() if p.expires_at > now
            ]


gate = ConfirmationGate()
