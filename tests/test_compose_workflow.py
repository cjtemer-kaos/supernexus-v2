import pytest
import json
from pathlib import Path
from src.core.compose_workflow import ComposeWorkflow, ComposeRun, ComposeStatus, ComposePhase


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "compose.db")


@pytest.fixture
def workflow(db_path):
    return ComposeWorkflow(director=None, db_path=db_path)


@pytest.mark.asyncio
async def test_create_run(workflow):
    run = await workflow.create(spec="Add a /api/health endpoint", goal="health", project="test")
    assert run.id
    assert run.spec == "Add a /api/health endpoint"
    assert run.goal == "health"
    assert run.status == ComposeStatus.PENDING


@pytest.mark.asyncio
async def test_execute_mock(workflow):
    run = await workflow.create(spec="Add logging middleware", goal="logging")
    result = await workflow.execute(run.id)
    assert result.status in (ComposeStatus.COMPLETED, ComposeStatus.FAILED)
    assert result.current_phase.value in [p.value for p in ComposePhase]


@pytest.mark.asyncio
async def test_execute_full_flow(workflow):
    run = await workflow.create(
        spec="Create a simple calculator API with add, subtract, multiply, divide",
        goal="calculator API",
        project="test",
    )
    result = await workflow.execute(run.id)
    assert result.phases.get("spec") is not None
    assert result.phases.get("plan") is not None
    assert result.phases.get("build") is not None
    for task in result.tasks:
        assert task.status in ("completed", "failed")


@pytest.mark.asyncio
async def test_persistence(workflow):
    run = await workflow.create(spec="test persistence", goal="persistence")
    await workflow.execute(run.id)
    loaded = workflow.get_run(run.id)
    assert loaded is not None
    assert loaded.spec == "test persistence"
    assert loaded.status == ComposeStatus.COMPLETED


def test_list_runs(workflow):
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(workflow.create(spec="run1", goal="r1", project="p1"))
        loop.run_until_complete(workflow.create(spec="run2", goal="r2", project="p1"))
        loop.run_until_complete(workflow.create(spec="run3", goal="r3", project="p2"))
    finally:
        loop.close()
    runs = workflow.list_runs(project="p1")
    assert len(runs) == 2
    runs_all = workflow.list_runs()
    assert len(runs_all) >= 3


def test_stats(workflow):
    stats = workflow.get_stats()
    assert "total_runs" in stats
    assert "db_path" in stats


@pytest.mark.asyncio
async def test_phases_create_plan_tasks(workflow):
    run = await workflow.create(spec="Build auth module", goal="auth")
    from src.core.compose_workflow import ComposePhase, ComposeTask
    await workflow._phase_spec(run)
    await workflow._phase_plan(run)
    assert len(run.tasks) > 0
    for t in run.tasks:
        assert t.id
        assert t.title


@pytest.mark.asyncio
async def test_review_gate(workflow):
    run = await workflow.create(spec="Simple endpoint", goal="api")
    run.phases["build"] = {"status": "ok", "tasks": [{"task_id": "1", "title": "add handler", "status": "completed"}]}
    from src.core.compose_workflow import ComposeTask
    task = ComposeTask(id="1", title="add handler", output="def handler(): return 42", status="completed")
    run.tasks = [task]
    result = await workflow._phase_review(run)
    assert "gate" in result
    assert result["gate"] in ("passed", "blocked")


@pytest.mark.asyncio
async def test_merge_summary(workflow):
    run = await workflow.create(spec="Merge test", goal="merge")
    from src.core.compose_workflow import ComposeTask
    task = ComposeTask(id="1", title="task1", output="print('ok')", status="completed")
    run.tasks = [task]
    result = await workflow._phase_merge(run)
    assert run.summary
    assert run.artifacts
