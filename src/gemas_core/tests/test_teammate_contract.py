"""v1.7.0 — teammate/contract: data class tests."""

from gemas_core.teammate.contract import (
    MailboxMessage,
    PeerStatus,
    PlanProposal,
    TeleportRequest,
)


class TestPeerStatus:
    def test_count(self):
        assert len(PeerStatus) == 3

    def test_values(self):
        assert PeerStatus.HEALTHY == "healthy"
        assert PeerStatus.DEGRADED == "degraded"
        assert PeerStatus.OFFLINE == "offline"

    def test_reachable(self):
        reachable = PeerStatus.reachable()
        assert PeerStatus.HEALTHY in reachable
        assert PeerStatus.DEGRADED in reachable
        assert PeerStatus.OFFLINE not in reachable
        assert len(reachable) == 2

    def test_lookup_by_value(self):
        assert PeerStatus("healthy") is PeerStatus.HEALTHY


class TestMailboxMessage:
    def test_construction_minimal(self):
        m = MailboxMessage(peer_id="peer-1", payload={"k": "v"})
        assert m.peer_id == "peer-1"
        assert m.payload == {"k": "v"}
        assert m.ttl_s == 3600
        assert m.msg_id  # auto-generated
        assert m.enqueued_at  # auto-generated

    def test_construction_full(self):
        m = MailboxMessage(
            peer_id="peer-1",
            payload={"k": "v"},
            ttl_s=60,
            enqueued_at="2026-06-06T00:00:00+00:00",
            msg_id="abc",
        )
        assert m.ttl_s == 60
        assert m.enqueued_at == "2026-06-06T00:00:00+00:00"
        assert m.msg_id == "abc"

    def test_is_expired_fresh(self):
        m = MailboxMessage(peer_id="x", payload={}, ttl_s=60)
        # Fresh message: not expired
        assert m.is_expired() is False

    def test_is_expired_old(self):
        m = MailboxMessage(
            peer_id="x",
            payload={},
            ttl_s=60,
            enqueued_at="2020-01-01T00:00:00+00:00",
        )
        # Old message: expired
        assert m.is_expired() is True

    def test_to_dict(self):
        m = MailboxMessage(
            peer_id="peer-1",
            payload={"hello": "world"},
            ttl_s=120,
            enqueued_at="2026-06-06T00:00:00+00:00",
            msg_id="msg-1",
        )
        d = m.to_dict()
        assert d["peer_id"] == "peer-1"
        assert d["payload"] == {"hello": "world"}
        assert d["ttl_s"] == 120
        assert d["enqueued_at"] == "2026-06-06T00:00:00+00:00"
        assert d["msg_id"] == "msg-1"

    def test_unique_msg_ids(self):
        a = MailboxMessage(peer_id="x", payload={})
        b = MailboxMessage(peer_id="x", payload={})
        assert a.msg_id != b.msg_id


class TestPlanProposal:
    def test_construction_defaults(self):
        p = PlanProposal()
        assert p.id
        assert p.steps == []
        assert p.requires == []
        assert p.approvals == {}
        assert p.proposed_by == "coordinator"
        assert p.proposed_at

    def test_construction_full(self):
        p = PlanProposal(
            steps=["a", "b", "c"],
            requires=["p1", "p2", "p3"],
            proposed_by="alice",
        )
        assert p.steps == ["a", "b", "c"]
        assert p.requires == ["p1", "p2", "p3"]
        assert p.proposed_by == "alice"

    def test_is_approved_no_requirements(self):
        # Empty requires = always approved (nothing to gate on)
        p = PlanProposal()
        assert p.is_approved() is True

    def test_is_approved_quorum(self):
        # 3 peers: needs 2 approvals
        p = PlanProposal(requires=["p1", "p2", "p3"])
        assert p.is_approved() is False
        p.record_approval("p1", True)
        assert p.is_approved() is False
        p.record_approval("p2", True)
        assert p.is_approved() is True  # 2/3 = quorum

    def test_is_approved_quorum_with_rejection(self):
        p = PlanProposal(requires=["p1", "p2", "p3"])
        p.record_approval("p1", True)
        p.record_approval("p2", False)
        p.record_approval("p3", True)
        # 2 yes out of 3 = quorum
        assert p.is_approved() is True

    def test_is_rejected(self):
        p = PlanProposal(requires=["p1", "p2"])
        p.record_approval("p1", True)
        p.record_approval("p2", False)
        assert p.is_rejected() is True

    def test_is_rejected_no_required_approvals(self):
        p = PlanProposal(requires=["p1"])
        # No approvals recorded yet
        assert p.is_rejected() is False

    def test_record_approval(self):
        p = PlanProposal(requires=["p1", "p2"])
        p.record_approval("p1", True)
        assert p.approvals == {"p1": True}
        p.record_approval("p1", False)  # can change mind
        assert p.approvals == {"p1": False}

    def test_to_dict(self):
        p = PlanProposal(
            steps=["s1", "s2"],
            requires=["p1"],
            proposed_by="bob",
        )
        p.record_approval("p1", True)
        d = p.to_dict()
        assert d["steps"] == ["s1", "s2"]
        assert d["requires"] == ["p1"]
        assert d["approvals"] == {"p1": True}
        assert d["proposed_by"] == "bob"
        assert d["id"] == p.id
        assert d["proposed_at"] == p.proposed_at


class TestTeleportRequest:
    def test_construction_minimal(self):
        t = TeleportRequest(
            from_peer="a",
            to_peer="b",
            session_state={"task": "x"},
        )
        assert t.from_peer == "a"
        assert t.to_peer == "b"
        assert t.session_state == {"task": "x"}
        assert t.request_id
        assert t.requested_at
        assert t.accepted is False

    def test_accept(self):
        t = TeleportRequest(from_peer="a", to_peer="b", session_state={})
        assert t.accepted is False
        t.accept()
        assert t.accepted is True

    def test_to_dict(self):
        t = TeleportRequest(
            from_peer="a",
            to_peer="b",
            session_state={"k": "v"},
            request_id="req-1",
            requested_at="2026-06-06T00:00:00+00:00",
        )
        t.accept()
        d = t.to_dict()
        assert d["from_peer"] == "a"
        assert d["to_peer"] == "b"
        assert d["session_state"] == {"k": "v"}
        assert d["request_id"] == "req-1"
        assert d["requested_at"] == "2026-06-06T00:00:00+00:00"
        assert d["accepted"] is True

    def test_unique_request_ids(self):
        a = TeleportRequest(from_peer="a", to_peer="b", session_state={})
        b = TeleportRequest(from_peer="a", to_peer="b", session_state={})
        assert a.request_id != b.request_id
