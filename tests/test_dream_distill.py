import pytest
import json
from src.core.dream_distill import DreamDistillEngine, DreamInsight, DreamCycle, DreamType


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "dream.db")


@pytest.fixture
def engine(db_path):
    return DreamDistillEngine(director=None, db_path=db_path)


@pytest.mark.asyncio
async def test_dream_cycle(engine):
    cycle = await engine.dream()
    assert cycle.id
    assert cycle.dream_type == "dream"
    assert cycle.cycle == 1
    assert cycle.status == "completed"
    assert cycle.insight_count >= 1


@pytest.mark.asyncio
async def test_distill_cycle(engine):
    await engine.dream()
    cycle = await engine.distill()
    assert cycle.id
    assert cycle.dream_type == "distill"
    assert cycle.cycle == 1
    assert cycle.status == "completed"
    assert cycle.insight_count >= 1


@pytest.mark.asyncio
async def test_insights_persist(engine):
    await engine.dream()
    await engine.distill()
    dream_insights = engine.get_insights(dream_type="dream")
    distill_insights = engine.get_insights(dream_type="distill")
    assert len(dream_insights) >= 1
    assert len(distill_insights) >= 1


def test_cycles_stored(engine):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(engine.dream())
        loop.run_until_complete(engine.dream())
    finally:
        loop.close()
    cycles = engine.get_cycles(dream_type="dream")
    assert len(cycles) == 2
    assert cycles[0]["cycle"] == 2


def test_logs(engine):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(engine.dream())
    finally:
        loop.close()
    logs = engine.get_logs()
    assert len(logs) >= 2


def test_stats(engine):
    stats = engine.get_stats()
    assert "dream_cycles" in stats
    assert "distill_cycles" in stats
    assert "db_path" in stats


@pytest.mark.asyncio
async def test_multiple_dream_cycles(engine):
    for _ in range(3):
        c = await engine.dream()
        assert c.status == "completed"
    cycles = engine.get_cycles(dream_type="dream")
    assert len(cycles) == 3
    assert cycles[0]["cycle"] == 3
    assert cycles[2]["cycle"] == 1


@pytest.mark.asyncio
async def test_dream_with_custom_observations(engine):
    custom_fn = lambda: [{"id": "obs1", "content": "test observation", "topic": "testing"}]
    engine.get_observations_fn = custom_fn
    cycle = await engine.dream()
    assert cycle.status == "completed"
    assert cycle.insight_count >= 1


def test_insight_creation():
    ins = DreamInsight(
        dream_type="dream",
        title="Test Insight",
        summary="A test",
        patterns=["p1", "p2"],
        recommendations=["r1"],
        confidence=0.8,
        topics=["t1"],
    )
    assert ins.id
    assert ins.dream_type == "dream"
    assert len(ins.patterns) == 2


def test_cycle_creation():
    cycle = DreamCycle(dream_type="dream", cycle=1)
    assert cycle.id
    assert cycle.status == "pending"


def test_load_compose_runs_empty(engine):
    runs = engine._load_recent_compose_runs(days=7)
    assert isinstance(runs, list)


@pytest.mark.asyncio
async def test_dream_failure_handling(engine):
    engine.director = True
    engine.get_observations_fn = lambda: [{"id": "obs1", "content": "fail test", "topic": "test"}]
    orig_llm = engine._llm_call
    async def fail_llm(prompt):
        raise RuntimeError("Simulated failure")
    engine._llm_call = fail_llm
    cycle = await engine.dream()
    assert cycle.status == "failed"
    engine._llm_call = orig_llm
    engine.director = None


@pytest.mark.asyncio
async def test_distill_without_prior_dream(engine):
    cycle = await engine.distill()
    assert cycle.status == "completed"
    assert cycle.insight_count >= 1
