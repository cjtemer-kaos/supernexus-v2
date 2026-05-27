import pytest
from src.core.token_monitor import TokenMonitor


def test_record_usage():
    tm = TokenMonitor()
    tm.record_usage("agent-a", 100)
    usage = tm.get_usage("agent-a")
    assert usage == 100


def test_budget_warning_at_80pct():
    tm = TokenMonitor()
    tm.set_budget("agent-a", 1000)
    alert = tm.record_usage("agent-a", 800)
    assert alert is not None
    assert alert.level == "warning"


def test_budget_block_at_95pct():
    tm = TokenMonitor()
    tm.set_budget("agent-a", 1000)
    alert = tm.record_usage("agent-a", 960)
    assert alert is not None
    assert alert.level == "block"


def test_usage_by_agent():
    tm = TokenMonitor()
    tm.record_usage("agent-a", 200)
    tm.record_usage("agent-b", 300)
    tm.record_usage("agent-a", 150)
    assert tm.get_usage("agent-a") == 350
    assert tm.get_usage("agent-b") == 300


def test_monitor_status():
    tm = TokenMonitor()
    tm.set_budget("agent-a", 5000)
    tm.record_usage("agent-a", 100)
    tm.record_usage("agent-b", 200)
    status = tm.status()
    assert status["total_records"] == 2
    assert status["budgets_configured"] == 1
    assert "agent-a" in status["agents"]
    assert "agent-b" in status["agents"]
