"""v1.7.0 — teammate/contract: portable data contracts for multi-agent coordination.

Ports the portable subset of RUFLO v3's
`plugins/teammate-plugin/src/teammate-bridge.ts`:

  - `PeerStatus`       — enum (healthy / degraded / offline)
  - `MailboxMessage`   — peer-to-peer async delivery
  - `PlanProposal`     — multi-agent plan with per-peer approval
  - `TeleportRequest`  — session handoff between peers

These are pure data classes; they DO NOT include any transport
implementation. Transport lives in the existing
`send_message` / `read_messages` MCP tools and the
`message_board.db` schema. The new MCP tools that USE these
contracts (`delegate_to_peer`, `approve_plan`, etc.) are
proposed as additive surface in v1.7 roadmap item 12 — not
implemented here.

Constraint compliance: the new `inbox` table would be ADDITIVE
to `message_board.db`, never replacing existing tables.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


# Polyfill: StrEnum was added in Python 3.11. We target 3.10.
try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    class StrEnum(str, Enum):
        """str + Enum polyfill for Python < 3.11."""

        def __new__(cls, value):
            obj = str.__new__(cls, value)
            obj._value_ = value
            return obj

        def __str__(self) -> str:
            return self._value_


def _now_iso() -> str:
    """ISO-8601 UTC timestamp (e.g. 2026-06-06T08:00:00Z)."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Short, time-ordered unique id (UUID4 hex)."""
    return uuid.uuid4().hex


class PeerStatus(StrEnum):
    """Liveness of a peer in the NexusHive network."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"

    @classmethod
    def reachable(cls) -> tuple["PeerStatus", ...]:
        """Peers that can receive a mailbox message right now."""
        return (cls.HEALTHY, cls.DEGRADED)


@dataclass
class MailboxMessage:
    """Async peer-to-peer delivery.

    Transport: a future `delegate_to_peer` MCP tool would insert
    rows into a new `inbox` table (additive to `message_board.db`).
    """

    peer_id: str
    payload: Dict[str, Any]
    ttl_s: int = 3600
    enqueued_at: str = field(default_factory=_now_iso)
    msg_id: str = field(default_factory=_new_id)

    def is_expired(self, now: Optional[str] = None) -> bool:
        """Check if the message has exceeded its TTL.

        ``now`` defaults to the current UTC time. Format must match
        the ISO-8601 produced by ``_now_iso()``.
        """
        if not now:
            now = _now_iso()
        # Both are ISO-8601 UTC; lexicographic compare is valid
        # because both have the same Z-suffix timezone.
        return now > _add_seconds(self.enqueued_at, self.ttl_s)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "msg_id": self.msg_id,
            "peer_id": self.peer_id,
            "payload": self.payload,
            "ttl_s": self.ttl_s,
            "enqueued_at": self.enqueued_at,
        }


@dataclass
class PlanProposal:
    """A multi-agent plan awaiting per-peer approval.

    ``approvals`` maps peer_id -> bool. A plan with N peers
    requires N/2 + 1 approvals to be considered accepted.
    """

    id: str = field(default_factory=_new_id)
    steps: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)  # peer IDs that must approve
    approvals: Dict[str, bool] = field(default_factory=dict)
    proposed_at: str = field(default_factory=_now_iso)
    proposed_by: str = "coordinator"

    def is_approved(self) -> bool:
        """Quorum rule: N/2 + 1 of the required approvers say True.

        Required peers that have NOT responded are counted as
        not-yet-approved (absent != approved).
        """
        if not self.requires:
            return True
        yes = sum(1 for p in self.requires if self.approvals.get(p) is True)
        return yes >= len(self.requires) // 2 + 1

    def is_rejected(self) -> bool:
        """A single required peer explicitly rejecting rejects the plan.

        Required peers that have NOT responded are not rejections —
        they are pending. Use ``is_approved()`` for quorum and
        ``pending_approvers()`` to find the missing ones.
        """
        return any(self.approvals.get(p) is False for p in self.requires)

    def pending_approvers(self) -> List[str]:
        """Required peers that have not yet responded."""
        return [p for p in self.requires if p not in self.approvals]

    def record_approval(self, peer_id: str, approved: bool) -> None:
        self.approvals[peer_id] = approved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "steps": list(self.steps),
            "requires": list(self.requires),
            "approvals": dict(self.approvals),
            "proposed_at": self.proposed_at,
            "proposed_by": self.proposed_by,
        }


@dataclass
class TeleportRequest:
    """Session handoff: one peer's working state moves to another."""

    from_peer: str
    to_peer: str
    session_state: Dict[str, Any]
    requested_at: str = field(default_factory=_now_iso)
    request_id: str = field(default_factory=_new_id)
    accepted: bool = False

    def accept(self) -> None:
        self.accepted = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "from_peer": self.from_peer,
            "to_peer": self.to_peer,
            "session_state": self.session_state,
            "requested_at": self.requested_at,
            "accepted": self.accepted,
        }


def _add_seconds(iso_ts: str, seconds: int) -> str:
    """Add ``seconds`` to an ISO-8601 timestamp and return ISO-8601."""
    # Strip the trailing 'Z' for fromisoformat; we add it back.
    ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    new_ts = ts.timestamp() + seconds
    return datetime.fromtimestamp(new_ts, tz=timezone.utc).isoformat()


__all__ = [
    "PeerStatus",
    "MailboxMessage",
    "PlanProposal",
    "TeleportRequest",
]
