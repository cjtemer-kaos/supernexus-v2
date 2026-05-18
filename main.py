#!/usr/bin/env python3
"""
SuperNEXUS v2.0 - Entry Point

DirectorNexus orchestrator with all subsystems:
- Connectivity (SSH, Tailscale, MCP, API)
- Memory (Neural SQLite, RAG TF-IDF, Knowledge Graph)
- Agents (15 gems with lazy loading)
- QA Loop (auto-improvement)
- Setup Wizard (zero-config secrets)
"""

import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("supernexus")


async def main():
    from src.core.director import DirectorNexus
    from src.core.connectivity import ConnectivityLayer
    from src.memory.neural_patterns import NeuralPatterns
    from src.memory.rag_memory import RAGMemory
    from src.memory.knowledge_graph import KnowledgeGraph
    from src.memory.qa_loop import QALoop
    from src.bridges.ssh_bridge import SSHBridge
    from src.skills.registry import SkillsRegistry

    print("=" * 60)
    print("  SuperNEXUS v2.0 - Director Level")
    print("=" * 60)
    print()

    # Initialize core components
    director = DirectorNexus(project="default")
    neural = NeuralPatterns()
    rag = RAGMemory()
    kg = KnowledgeGraph()
    qa = QALoop()
    ssh = SSHBridge()
    connectivity = ConnectivityLayer()
    skills = SkillsRegistry()

    # Check engine status
    print("Engines:")
    status = await connectivity.check_all_engines()
    for name, state in status.items():
        icon = "[OK]" if state == "online" else "[--]"
        print(f"  {icon} {name}: {state}")
    print()

    # Show SSH machines
    print("SSH Machines:")
    for name, caps in ssh.list_machines().items():
        print(f"  [{name}] {', '.join(caps)}")
    print()

    # Show memory stats
    print("Memory:")
    neural_stats = neural.get_stats()
    rag_stats = rag.get_stats()
    kg_stats = kg.get_stats()
    print(f"  Neural: {neural_stats.get('total_patterns', 0)} patterns")
    print(f"  RAG:    {rag_stats.get('total_entries', 0)} entries")
    print(f"  Graph:  {kg_stats.get('total_notes', 0)} notes")
    print()

    # Show skills
    skills_stats = skills.get_stats()
    print(f"Skills: {skills_stats['total_indexed']} indexed, {skills_stats['loaded_in_memory']} loaded")
    print()

    # Show director status
    dstatus = director.get_status()
    print(f"Director: {dstatus['identity']['name']} v{dstatus['identity']['version']}")
    print(f"Project: {dstatus['current_project']}")
    print(f"Gemas: {dstatus['gemas_count']}")
    print()

    # Show QA stats
    qa_stats = qa.get_stats()
    print(f"QA Loop: {qa_stats['total_evaluations']} evaluations, {qa_stats['success_rate']:.0%} success rate")
    print()

    # Test task classification
    test_tasks = [
        "Investiga como configurar OAuth 2.0",
        "Debuggea este error de Python",
        "Crea un deploy en Docker para Remote Node",
    ]

    print("Task Classification Tests:")
    for task in test_tasks:
        classification = await director.classify_task(task)
        print(f"  Task: {task[:50]}...")
        print(f"    Gems: {classification.selected_gems}")
        print(f"    Engines: {classification.selected_engines}")
        print(f"    Parallel: {classification.can_parallelize}")
        print()

    # Cleanup
    await connectivity.close()

    print("=" * 60)
    print("  SuperNEXUS v2.0 - Ready")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
