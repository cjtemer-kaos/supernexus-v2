#!/usr/bin/env python3
"""
Integration Tests - SuperNEXUS v2.0

End-to-end tests for all subsystems.
"""

import asyncio
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("tests")


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        logger.info(f"  [PASS] {name}")

    def fail(self, name: str, error: str = ""):
        self.failed += 1
        self.errors.append((name, error))
        logger.error(f"  [FAIL] {name}: {error}")

    def summary(self) -> str:
        total = self.passed + self.failed
        return f"Tests: {total}, Passed: {self.passed}, Failed: {self.failed}"


async def test_connectivity(r: TestResult):
    """Test connectivity layer"""
    from src.core.connectivity import ConnectivityLayer

    conn = ConnectivityLayer()
    try:
        status = await conn.check_all_engines()
        for name, state in status.items():
            if state == "online":
                r.ok(f"Engine {name} online")
            else:
                r.fail(f"Engine {name}", f"Status: {state}")
        await conn.close()
    except Exception as e:
        r.fail("Connectivity", str(e))


async def test_director(r: TestResult):
    """Test DirectorNexus"""
    from src.core.director import DirectorNexus

    try:
        director = DirectorNexus(project="test")
        status = director.get_status()

        if status["identity"]["name"] == "DirectorNexus":
            r.ok("Director identity")
        else:
            r.fail("Director identity", f"Got: {status['identity']['name']}")

        if status["gemas_count"] == 15:
            r.ok("Director 15 gems")
        else:
            r.fail("Director gems", f"Count: {status['gemas_count']}")

        # Test classification
        classification = await director.classify_task("Debug this Python error")
        if "debugger" in classification.selected_gems:
            r.ok("Task classification (debug)")
        else:
            r.fail("Task classification", f"Gems: {classification.selected_gems}")

        classification2 = await director.classify_task("Investiga sobre OAuth")
        if "scholar" in classification2.selected_gems:
            r.ok("Task classification (research)")
        else:
            r.fail("Task classification (research)", f"Gems: {classification2.selected_gems}")

    except Exception as e:
        r.fail("Director", str(e))


async def test_memory(r: TestResult):
    """Test memory layers"""
    from src.memory.neural_patterns import NeuralPatterns
    from src.memory.rag_memory import RAGMemory
    from src.memory.knowledge_graph import KnowledgeGraph

    try:
        # Neural
        neural = NeuralPatterns()
        stats = neural.get_stats()
        r.ok(f"Neural memory initialized ({stats.get('total_patterns', 0)} patterns)")

        # RAG
        rag = RAGMemory()
        rag.add("test_001", "Python is a programming language", "test", ["python"])
        results = rag.search("programming language")
        if len(results) > 0:
            r.ok(f"RAG search ({len(results)} results)")
        else:
            r.fail("RAG search", "No results")

        rag_stats = rag.get_stats()
        r.ok(f"RAG stats ({rag_stats.get('total_entries', 0)} entries)")

        # Knowledge Graph
        kg = KnowledgeGraph()
        kg_stats = kg.get_stats()
        r.ok(f"Knowledge graph ({kg_stats.get('total_notes', 0)} notes)")

    except Exception as e:
        r.fail("Memory", str(e))


async def test_event_bus(r: TestResult):
    """Test event bus"""
    from src.core.event_bus import EventBus, Message, EventType

    try:
        bus = EventBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("message", handler)
        msg = Message(source="test", target="*", event_type=EventType.MESSAGE, content="hello")
        await bus.publish(msg)

        if len(received) == 1 and received[0].content == "hello":
            r.ok("Event bus publish/subscribe")
        else:
            r.fail("Event bus", f"Received: {len(received)} messages")

        stats = bus.get_stats()
        if stats["total_messages"] == 1:
            r.ok("Event bus stats")
        else:
            r.fail("Event bus stats", f"Count: {stats['total_messages']}")

    except Exception as e:
        r.fail("Event bus", str(e))


async def test_communication(r: TestResult):
    """Test agent communication"""
    from src.core.event_bus import EventBus
    from src.core.communication import CommunicationFlow, AgentCapability

    try:
        bus = EventBus()
        comm = CommunicationFlow(bus)

        async def echo_handler(msg):
            return f"Echo: {msg.content}"

        comm.register_agent("echo", AgentCapability(
            name="echo", description="Echo", tags=["test"], can_handle=["test"]
        ), echo_handler)

        result = await comm.send_message("test", "echo", "hello world")
        if result.get("success") and "Echo" in str(result.get("response", "")):
            r.ok("SendMessage pattern")
        else:
            r.fail("SendMessage", f"Result: {result}")

        stats = comm.get_stats()
        if stats["registered_agents"] == 1:
            r.ok("Communication stats")
        else:
            r.fail("Communication stats", f"Agents: {stats['registered_agents']}")

    except Exception as e:
        r.fail("Communication", str(e))


async def test_tools(r: TestResult):
    """Test builtin tools"""
    from src.tools.builtin import WorkspaceTools, ExecuteTools, ParseTools

    try:
        ws = WorkspaceTools()
        result = ws.list_dir("")
        if "entries" in result:
            r.ok(f"Workspace list_dir ({result.get('count', 0)} entries)")
        else:
            r.fail("Workspace list_dir", str(result))

        exec_tools = ExecuteTools()
        exec_result = await exec_tools.execute_command("echo hello")
        if exec_result.get("success") and "hello" in exec_result.get("stdout", ""):
            r.ok("Execute command")
        else:
            r.fail("Execute command", str(exec_result))

    except Exception as e:
        r.fail("Tools", str(e))


async def test_qa_loop(r: TestResult):
    """Test QA loop"""
    from src.memory.qa_loop import QALoop

    try:
        qa = QALoop()
        qa.evaluate_response("test query", "test response", "coder", True)
        qa.evaluate_response("test query 2", "error response", "coder", False, "timeout")

        stats = qa.get_stats()
        if stats["total_evaluations"] >= 2:
            r.ok(f"QA loop ({stats['total_evaluations']} evaluations)")
        else:
            r.fail("QA loop", f"Evaluations: {stats['total_evaluations']}")

        failures = qa.get_recent_failures()
        if len(failures) > 0:
            r.ok(f"QA failures tracking ({len(failures)} failures)")
        else:
            r.fail("QA failures", "No failures tracked")

    except Exception as e:
        r.fail("QA loop", str(e))


async def test_ollama(r: TestResult):
    """Test Ollama integration"""
    from src.core.ollama import OllamaClient, LLMRouter

    try:
        ollama = OllamaClient()
        available = await ollama.is_available()

        if available:
            r.ok("Ollama available")
            models = await ollama.list_models()
            r.ok(f"Ollama models ({len(models)} models)")
        else:
            r.fail("Ollama", "Not available (this is OK if Ollama is not running)")

        # Test router (doesn't need Ollama)
        router = LLMRouter(ollama)
        routing = await router.route_task("Write a Python function")
        if routing.get("gem") == "coder":
            r.ok("LLM routing (code)")
        else:
            r.fail("LLM routing", f"Gem: {routing.get('gem')}")

        await ollama.close()
    except Exception as e:
        r.fail("Ollama", str(e))


async def test_pc2_bridge(r: TestResult):
    """Test PC2 bridge"""
    from src.bridges.pc2_bridge import PC2Bridge

    try:
        pc2 = PC2Bridge()
        status = pc2.get_status()

        if status["host"] == "192.168.1.50":
            r.ok("PC2 bridge config")
        else:
            r.fail("PC2 bridge config", f"Host: {status['host']}")

        # Don't actually connect (may not be available)
        r.ok("PC2 bridge initialized")
    except Exception as e:
        r.fail("PC2 bridge", str(e))


async def test_active_learning(r: TestResult):
    """Test active learning loop structure"""
    from src.memory.active_learning import ActiveLearningLoop

    try:
        learning = ActiveLearningLoop()
        stats = learning.get_learning_stats()
        r.ok(f"Active learning initialized ({stats.get('total_learnings', 0)} learnings)")
        await learning.close()
    except Exception as e:
        r.fail("Active learning", str(e))


async def main():
    print("=" * 60)
    print("  SuperNEXUS v2.0 - Integration Tests")
    print("=" * 60)
    print()

    r = TestResult()

    tests = [
        ("Connectivity", test_connectivity),
        ("Director", test_director),
        ("Memory", test_memory),
        ("Event Bus", test_event_bus),
        ("Communication", test_communication),
        ("Tools", test_tools),
        ("QA Loop", test_qa_loop),
        ("Ollama", test_ollama),
        ("PC2 Bridge", test_pc2_bridge),
        ("Active Learning", test_active_learning),
    ]

    for name, test_func in tests:
        print(f"\nTesting {name}...")
        await test_func(r)

    print()
    print("=" * 60)
    print(f"  {r.summary()}")
    print("=" * 60)

    if r.failed > 0:
        print("\nFailed tests:")
        for name, error in r.errors:
            print(f"  - {name}: {error}")

    return r.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
