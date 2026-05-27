import pytest
from src.core.a2a_server import A2AServer, A2ATask, A2ATaskState, A2AAgentCard


def test_agent_card():
    card = A2AAgentCard()
    d = card.to_dict()
    assert d["name"] == "NEXUS Director"
    assert "code" in d["capabilities"]["skills"]
    assert "a2a" in d["protocols"]


def test_create_task():
    server = A2AServer()
    task = server.create_task("Refactor the auth module", submitter="antigravity")
    assert task.description == "Refactor the auth module"
    assert task.state == A2ATaskState.SUBMITTED
    assert task.submitter == "antigravity"
    assert task.id in server._tasks


def test_get_task():
    server = A2AServer()
    task = server.create_task("test")
    retrieved = server.get_task(task.id)
    assert retrieved is not None
    assert retrieved.id == task.id
    assert server.get_task("nonexistent") is None


def test_cancel_task():
    server = A2AServer()
    task = server.create_task("cancel me")
    assert server.cancel_task(task.id) is True
    assert task.state == A2ATaskState.CANCELED
    # Already canceled cannot be canceled again
    assert server.cancel_task(task.id) is False


@pytest.mark.asyncio
async def test_execute_task_with_executor():
    async def executor(desc: str) -> dict:
        return {"result": f"done: {desc}"}
    server = A2AServer(executor=executor)
    task = server.create_task("generate report")
    result = await server.execute_task(task.id)
    assert result.state == A2ATaskState.COMPLETED
    assert result.output_data["result"] == "done: generate report"


@pytest.mark.asyncio
async def test_execute_task_no_executor():
    server = A2AServer()
    task = server.create_task("will fail")
    result = await server.execute_task(task.id)
    assert result.state == A2ATaskState.FAILED
    assert "No executor" in result.error


def test_list_tasks_filter():
    server = A2AServer()
    server.create_task("task 1")
    server.create_task("task 2")
    assert len(server.list_tasks()) == 2
    # After canceling one
    t3 = server.create_task("task 3")
    server.cancel_task(t3.id)
    canceled = server.list_tasks(state="canceled")
    assert len(canceled) == 1


def test_server_status():
    server = A2AServer()
    server.create_task("task a")
    server.create_task("task b")
    status = server.status()
    assert status["total_tasks"] == 2
    assert "submitted" in status["by_state"]
