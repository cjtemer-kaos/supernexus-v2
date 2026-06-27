"""Fuzzy autocompletion for NEXUS Console."""
from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


# Static command tree: command -> [subcommands]
COMMAND_TREE: dict[str, list[str]] = {
    "/chat": [],
    "/status": [],
    "/agent": ["list", "tell", "loop"],
    "/brain": ["stats", "recall", "learn", "knowledge", "export"],
    "/memory": ["search", "stats", "consolidate", "health"],
    "/hive": ["status", "send"],
    "/system": ["stats", "safe"],
    "/doctor": [],
    "/health": [],
    "/tokens": [],
    "/model": [],
    "/skill": ["list", "install"],
    "/conductor": ["spawn", "list", "merge", "cleanup"],
    "/devloop": ["run", "status"],
    "/absorb": ["repo", "status"],
    "/help": [],
    "/clear": [],
    "/theme": ["nexus", "dark", "cyberpunk", "minimal"],
    "/login": [],
    "/exit": [],
}

# Short descriptions for help
COMMAND_HELP: dict[str, str] = {
    "/chat": "Chat with Director (streaming)",
    "/status": "System status overview",
    "/agent": "Manage agents/gemas",
    "/brain": "Cerebro knowledge base",
    "/memory": "Memory operations",
    "/hive": "Inter-agent messaging",
    "/system": "System stats and safety",
    "/doctor": "Run diagnostics",
    "/health": "Circuit breaker health",
    "/tokens": "Token usage report",
    "/model": "Show/switch active model",
    "/skill": "Skill marketplace",
    "/conductor": "Conductor worktree manager",
    "/devloop": "Development loop",
    "/absorb": "Code absorption",
    "/help": "Show help",
    "/clear": "Clear screen",
    "/theme": "Switch UI theme",
    "/login": "Authenticate with API",
    "/exit": "Quit console",
}


class NexusCompleter(Completer):
    """Fuzzy completer that handles /commands and their subcommands."""

    def __init__(self):
        self._dynamic_agents: list[str] = []
        self._dynamic_skills: list[str] = []

    def set_agents(self, agents: list[str]):
        self._dynamic_agents = agents

    def set_skills(self, skills: list[str]):
        self._dynamic_skills = skills

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor.lstrip()

        # Empty or just "/" -> suggest all commands
        if not text or text == "/":
            for cmd in sorted(COMMAND_TREE):
                desc = COMMAND_HELP.get(cmd, "")
                yield Completion(cmd, start_position=-len(text), display_meta=desc)
            return

        parts = text.split()
        cmd = parts[0]

        # Partial first word -> fuzzy match commands
        if len(parts) == 1 and not text.endswith(" "):
            query = cmd.lower()
            for c in sorted(COMMAND_TREE):
                if query in c.lower() or _fuzzy_match(query, c):
                    desc = COMMAND_HELP.get(c, "")
                    yield Completion(c, start_position=-len(cmd), display_meta=desc)
            return

        # Second word -> subcommands
        if cmd in COMMAND_TREE and len(parts) <= 2:
            subs = COMMAND_TREE[cmd]
            # Dynamic completions for specific commands
            if cmd == "/agent" and "tell" in parts:
                subs = subs + self._dynamic_agents
            elif cmd == "/skill" and "install" in parts:
                subs = subs + self._dynamic_skills

            partial = parts[1] if len(parts) == 2 and not text.endswith(" ") else ""
            for s in subs:
                if not partial or partial.lower() in s.lower():
                    yield Completion(s, start_position=-len(partial))


def _fuzzy_match(query: str, target: str) -> bool:
    """Simple fuzzy: all chars of query appear in order in target."""
    it = iter(target.lower())
    return all(c in it for c in query.lower())
