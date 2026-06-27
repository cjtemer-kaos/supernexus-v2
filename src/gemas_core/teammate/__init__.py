"""teammate package — multi-agent coordination contracts.

Currently a thin layer over `contract.py`. Future v1.8+ work may
add `teammate/coordinator.py` (helper that uses these dataclasses
to drive the existing `send_message` MCP tool) and
`teammate/transport.py` (sqlite-backed mailbox — additive to
`message_board.db`).
"""
from .contract import (
    MailboxMessage,
    PeerStatus,
    PlanProposal,
    TeleportRequest,
)

__all__ = ["PeerStatus", "MailboxMessage", "PlanProposal", "TeleportRequest"]
