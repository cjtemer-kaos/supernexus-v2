"""Director Service — init sovereign director subsystems on DirectorNexus."""
from __future__ import annotations
import logging
from src.core import nexus_config

logger = logging.getLogger(__name__)


class DirectorService:

    @staticmethod
    def init_director(director):
        from src.core.decision_engine import DecisionEngine
        from src.core.command_protocol import CommandDispatcher
        from src.core.sub_director import SubDirectorRegistry
        from src.core.external_agent import ExternalAgentRegistry
        from src.core.learning_loop import LearningLoop
        from src.core.decision_engine import LLMAdapter

        director.decision_engine = DecisionEngine()
        for name, gema in director.gemas.items():
            if hasattr(gema, 'tags'):
                director.decision_engine.capabilities.register(f"gema-{name}", gema.tags)

        director.command_dispatcher = CommandDispatcher(default_timeout_s=300)
        director.sub_directors = SubDirectorRegistry.create_defaults()
        for sd in director.sub_directors.sub_directors:
            target = f"sub-director-{sd.config.name}"
            director.command_dispatcher.register(
                target, lambda cmd, sd=sd: director._sub_director_handle(sd, cmd))

        for sd in director.sub_directors.sub_directors:
            for agent_name in sd.config.agents:
                if agent_name.startswith("gema-"):
                    director.command_dispatcher.register(agent_name, director._gema_handle)
        for gema_name in director.decision_engine.capabilities.agents:
            if gema_name.startswith("gema-") and gema_name not in director.command_dispatcher._handlers:
                director.command_dispatcher.register(gema_name, director._gema_handle)

        director.external_agents = ExternalAgentRegistry()
        _register_default_external_agents(director)
        for agent in director.external_agents.agents:
            if agent.name in ("hermes", "openclaw", "agent-zero", "oma-orchestrator"):
                director.command_dispatcher.register(
                    agent.name,
                    lambda cmd, name=agent.name: director._execute_external_agent(name, cmd))

        director.learning_loop = LearningLoop()
        for name, gema in director.gemas.items():
            if hasattr(gema, 'tags'):
                director.learning_loop.register_known(*gema.tags)

        connectivity = getattr(director, 'connectivity', None)
        director.llm_adapter = LLMAdapter(
            llm_call=director._llm_enhance_call if connectivity else None)

        logger.info(
            f"Sovereign Director initialized: {len(director.sub_directors.sub_directors)} sub-directors, "
            f"{len(director.external_agents.agents)} external agents, "
            f"LLM adapter: {director.llm_adapter.available}")


def _register_default_external_agents(director):
    from src.core.external_agent import ExternalAgent
    defaults = [
        ExternalAgent(name="antigravity", capabilities=["research", "download", "analyze", "repos"],
                     protocol="messageboard", endpoint="antigravity", cost="free"),
        ExternalAgent(name="opencode", capabilities=["code", "refactor", "implement", "fix"],
                     protocol="messageboard", endpoint="opencode", cost="free"),
        ExternalAgent(name="director-llm", capabilities=["reasoning", "analysis", "code", "research"],
                     protocol="http", endpoint=nexus_config.get_nexus_url() + "/api/chat", cost="free"),
        ExternalAgent(name="claude-code", capabilities=["code", "refactor", "debug", "test", "architect"],
                     protocol="cli", endpoint="claude", cost="token-based", max_concurrent=1),
        ExternalAgent(name="aider", capabilities=["code", "refactor", "git"],
                     protocol="cli", endpoint="aider", cost="free"),
        ExternalAgent(name="agent-zero", capabilities=["code", "research", "browser", "terminal"],
                         protocol="cli", endpoint="docker", cost="free",
                         metadata={"docker_cmd": "docker exec agent-zero /opt/venv-a0/bin/python /zero_helper.py"}),
        ExternalAgent(name="hermes", capabilities=["cli", "code", "messaging", "telegram"],
                         protocol="cli", endpoint="hermes", cost="free",
                         metadata={"cli_args": ["-z", "-m", "ollama/qwen3.5:4b"]}),
        ExternalAgent(name="openclaw", capabilities=["code", "llm", "generic", "reasoning"],
                         protocol="cli", endpoint="openclaw", cost="free",
                         metadata={"cli_args": ["infer", "model", "run", "--model", "ollama/qwen2.5-coder:7b", "--local", "--json"]}),
        ExternalAgent(name="pc2-hermes", capabilities=["cli", "code", "messaging", "research"],
                         protocol="http", endpoint="http://${REMOTE_HOST}:9000/api/external/hermes", cost="free"),
        ExternalAgent(name="pc2-openclaw", capabilities=["code", "llm", "generic", "reasoning"],
                         protocol="http", endpoint="http://${REMOTE_HOST}:9000/api/external/openclaw", cost="free"),
        ExternalAgent(name="pc2-ollama", capabilities=["code", "reasoning", "gpu"],
                         protocol="http", endpoint="http://${REMOTE_HOST}:11434/api/chat", cost="free"),
        ExternalAgent(name="n8n", capabilities=["workflow", "automation", "webhook"],
                         protocol="http", endpoint="http://localhost:5678", cost="free"),
        ExternalAgent(name="pc2-goose", capabilities=["code", "research", "browser", "mcp"],
                         protocol="ssh", endpoint="http://${REMOTE_HOST}:9000/api/chat", cost="free",
                         metadata={"cli_command": "D:\\nexus\\bin\\Goose.exe run"}),
        ExternalAgent(name="pc2-pincer", capabilities=["code", "messaging", "whatsapp", "telegram", "slack", "email"],
                         protocol="ssh", endpoint="http://${REMOTE_HOST}:9000/api/chat", cost="free",
                         metadata={"cli_command": "pincer run --help"}),
        ExternalAgent(name="pc2-lethe", capabilities=["memory", "attention", "cognition", "reasoning"],
                         protocol="ssh", endpoint="http://${REMOTE_HOST}:9000/api/chat", cost="free",
                         metadata={"cli_command": "python -c \"import lethe; print('lethe OK')\""}),
        ExternalAgent(name="pc2-mem0", capabilities=["memory", "entity-linking", "temporal-reasoning", "hybrid-search"],
                         protocol="ssh", endpoint="http://${REMOTE_HOST}:9000/api/chat", cost="free",
                         metadata={"cli_command": "python -c \"from mem0 import Memory; m=Memory(); print('mem0 OK')\""}),
        ExternalAgent(name="pc2-qwen-code", capabilities=["code", "reasoning", "gpu"],
                         protocol="http", endpoint="http://${REMOTE_HOST}:11434/api/chat", cost="free",
                         metadata={"model": "qwen2.5-coder:7b"}),
        ExternalAgent(name="pc2-ollama-direct", capabilities=["code", "reasoning", "gpu"],
                          protocol="http", endpoint="http://${REMOTE_HOST}:11434/api/chat", cost="free"),
        ExternalAgent(name="oma-orchestrator", capabilities=["multi-agent", "parallel", "task-decomposition", "coordination", "code", "reasoning"],
                          protocol="cli", endpoint="oma", cost="free",
                          metadata={"cli_args": [], "oma_service": True}),
    ]
    for agent in defaults:
        director.external_agents.register(agent)

