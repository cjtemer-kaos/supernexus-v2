"""OMA Service — Hybrid NEXUS + Open Multi-Agent integration.

NEXUS acts as the coordinator (decides WHAT to do), OMA acts as the executor
(runs multiple agents in parallel with different models).

Usage:
    from src.services.oma_service import OMAService
    
    result = await OMAService.run_team(
        goal="Create a REST API for todos",
        agents=[
            {"name": "architect", "model": "qwen2.5-coder:7b", "provider": "ollama", "systemPrompt": "Design APIs"},
            {"name": "developer", "model": "qwen2.5-coder:7b", "provider": "ollama", "systemPrompt": "Write code"},
        ],
        options={"maxConcurrency": 2}
    )
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Path to OMA project
OMA_PROJECT_PATH = os.environ.get("OMA_PROJECT_PATH", "")


class OMAService:
    """Bridge between NEXUS and open-multi-agent (OMA)."""

    @staticmethod
    async def run_team(
        goal: str,
        agents: list[dict[str, Any]],
        options: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Execute a multi-agent team via OMA.
        
        Args:
            goal: The high-level goal to accomplish
            agents: List of agent configurations (name, model, provider, systemPrompt, etc.)
            options: Execution options (maxConcurrency, sharedMemory, defaultModel, etc.)
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with success, agentResults, totalTokenUsage, events
        """
        config = {
            "goal": goal,
            "agents": agents,
            "options": options or {},
        }
        
        return await OMAService._execute(config, timeout)

    @staticmethod
    async def run_tasks(
        goal: str,
        agents: list[dict[str, Any]],
        tasks: list[dict[str, Any]],
        options: dict[str, Any] | None = None,
        timeout: int = 300,
    ) -> dict[str, Any]:
        """Execute an explicit task pipeline via OMA.
        
        Args:
            goal: The high-level goal
            agents: List of agent configurations
            tasks: List of tasks with title, description, assignee, dependsOn
            options: Execution options
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with success, agentResults, totalTokenUsage, events
        """
        config = {
            "goal": goal,
            "agents": agents,
            "options": {
                **(options or {}),
                "tasks": tasks,
            },
        }
        
        return await OMAService._execute(config, timeout)

    @staticmethod
    async def _execute(config: dict[str, Any], timeout: int) -> dict[str, Any]:
        """Execute OMA runner with the given config."""
        import sys
        if sys.platform == "win32":
            cmd = ["npx.cmd", "tsx", "nexus-runner.ts"]
        else:
            cmd = ["npx", "tsx", "nexus-runner.ts"]
        
        input_json = json.dumps(config, ensure_ascii=False)
        logger.info(f"OMA: Executing {len(config['agents'])} agents for goal: {config['goal'][:60]}...")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=OMA_PROJECT_PATH,
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_json.encode("utf-8")),
                timeout=timeout,
            )
            
            # Log stderr (progress events) for debugging
            if stderr:
                progress_lines = stderr.decode("utf-8", errors="replace").strip().split("\n")
                for line in progress_lines:
                    if line.strip():
                        logger.info(f"OMA progress: {line.strip()}")
            
            if proc.returncode != 0:
                error = stdout.decode("utf-8", errors="replace")[:500]
                logger.error(f"OMA failed (exit {proc.returncode}): {error}")
                return {
                    "success": False,
                    "error": error,
                    "agentResults": {},
                    "totalTokenUsage": {"input_tokens": 0, "output_tokens": 0},
                    "events": [],
                }
            
            output = stdout.decode("utf-8", errors="replace")
            result = json.loads(output)
            logger.info(
                f"OMA complete: success={result.get('success')}, "
                f"agents={len(result.get('agentResults', {}))}, "
                f"tokens={result.get('totalTokenUsage', {})}"
            )
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"OMA timeout after {timeout}s")
            return {
                "success": False,
                "error": f"OMA timeout after {timeout}s",
                "agentResults": {},
                "totalTokenUsage": {"input_tokens": 0, "output_tokens": 0},
                "events": [],
            }
        except json.JSONDecodeError as e:
            logger.error(f"OMA JSON decode error: {e}")
            return {
                "success": False,
                "error": f"OMA JSON decode error: {e}",
                "agentResults": {},
                "totalTokenUsage": {"input_tokens": 0, "output_tokens": 0},
                "events": [],
            }
        except Exception as e:
            logger.error(f"OMA execution error: {e}")
            return {
                "success": False,
                "error": f"OMA execution error: {e}",
                "agentResults": {},
                "totalTokenUsage": {"input_tokens": 0, "output_tokens": 0},
                "events": [],
            }

    @staticmethod
    def create_ollama_agent(
        name: str,
        model: str = "qwen2.5-coder:7b",
        system_prompt: str = "",
        base_url: str = "http://localhost:11434/v1",
        max_turns: int = 5,
        tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create an Ollama agent configuration for OMA.
        
        Args:
            name: Agent name
            model: Ollama model name
            system_prompt: System prompt
            base_url: Ollama API endpoint
            max_turns: Maximum conversation turns
            tools: List of tool names (e.g., ['bash', 'file_read', 'file_write'])
            
        Returns:
            Agent configuration dict
        """
        agent = {
            "name": name,
            "model": model,
            "provider": "ollama",
            "systemPrompt": system_prompt,
            "maxTurns": max_turns,
            "baseURL": base_url,
            "apiKey": "ollama",
        }
        if tools:
            agent["tools"] = tools
        return agent

    @staticmethod
    def create_claude_agent(
        name: str,
        model: str = "claude-sonnet-4-6",
        system_prompt: str = "",
        max_turns: int = 5,
        tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a Claude agent configuration for OMA."""
        agent = {
            "name": name,
            "model": model,
            "provider": "anthropic",
            "systemPrompt": system_prompt,
            "maxTurns": max_turns,
        }
        if tools:
            agent["tools"] = tools
        return agent
