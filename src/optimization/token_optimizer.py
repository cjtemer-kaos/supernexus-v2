"""
Token Optimizer para SuperNEXUS v2
15 reglas para optimizar tokens basado en mejores practicas
"""

import logging
import math
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Model(Enum):
    HAIKU = {"name": "claude-haiku-4-5", "input_cost": 0.80, "output_cost": 4.00, "speed": "instant"}
    SONNET = {"name": "claude-sonnet-4", "input_cost": 3.00, "output_cost": 15.00, "speed": "fast"}
    OPUS = {"name": "claude-opus-4", "input_cost": 15.00, "output_cost": 75.00, "speed": "thorough"}
    OLLAMA = {"name": "ollama-local", "input_cost": 0.0, "output_cost": 0.0, "speed": "variable"}


class TokenOptimizer:
    """Implementa 15 reglas para optimizar tokens"""

    def __init__(self):
        self.session_tokens = 0
        self.session_cost = 0.0
        self.rules_applied = []

    def select_model(self, task_type: str, complexity: str) -> Dict:
        rules = {
            ("simple", "quick"): Model.HAIKU,
            ("categorization", "low"): Model.HAIKU,
            ("classification", "low"): Model.HAIKU,
            ("summarization", "simple"): Model.HAIKU,
            ("coding", "medium"): Model.SONNET,
            ("analysis", "medium"): Model.SONNET,
            ("design", "medium"): Model.SONNET,
            ("architecture", "complex"): Model.SONNET,
            ("research", "deep"): Model.SONNET,
            ("reasoning", "complex"): Model.SONNET,
            ("local", "any"): Model.OLLAMA,
        }
        selected = rules.get((task_type, complexity), Model.SONNET)
        self.rules_applied.append("Rule 1: Model Selection")
        return {
            "model": selected.value["name"],
            "strategy": f"Use {selected.value['name']} for {task_type} ({complexity})",
            "cost_per_1k_input": selected.value["input_cost"],
            "cost_per_1k_output": selected.value["output_cost"],
        }

    def smart_cache(self, context: str, reuse_count: int = 3) -> Dict:
        tokens = len(context.split())
        cache_tokens = tokens // 100
        reuse_savings = cache_tokens * reuse_count * 0.5
        self.rules_applied.append("Rule 2: Smart Caching")
        return {
            "cache_opportunity": cache_tokens > 1024,
            "tokens_cacheable": cache_tokens,
            "estimated_savings": f"${reuse_savings * 0.000001:.2f}" if reuse_count > 1 else "Set context once",
        }

    def batch_processing(self, tasks: List[str]) -> Dict:
        single_task_cost = 100
        batch_cost = single_task_cost + (len(tasks) * 50)
        savings = (single_task_cost * len(tasks)) - batch_cost
        self.rules_applied.append("Rule 3: Batch Processing")
        return {"efficiency": f"Procesa {len(tasks)} tareas en 1 contexto", "tokens_saved": savings}

    def code_reference(self, file_path: str, function_name: str = None, lines: tuple = None) -> Dict:
        self.rules_applied.append("Rule 4: Specific Code Reference")
        full_file_cost = 500
        reference_cost = 20
        return {
            "tokens_saved": full_file_cost - reference_cost,
            "technique": "Use file_path::function_name notation",
            "example": f"{file_path}::{function_name}" if function_name else f"{file_path} (lines {lines[0]}-{lines[1]})",
            "savings_percent": f"{((full_file_cost - reference_cost) / full_file_cost * 100):.0f}%",
        }

    def avoid_repetition(self, message: str) -> Dict:
        repetitions = message.count("earlier") + message.count("as mentioned") + message.count("I said")
        self.rules_applied.append("Rule 5: Avoid Repetition")
        return {"redundancy_found": repetitions > 0, "strategy": "Use pronouns and references"}

    def load_only_needed_mcp(self, all_mcp: List[str], needed: List[str]) -> Dict:
        unused = [m for m in all_mcp if m not in needed]
        tokens_saved = len(unused) * 50
        self.rules_applied.append("Rule 6: Load Only Needed MCP")
        return {"total_mcp": len(all_mcp), "to_load": len(needed), "to_skip": len(unused), "tokens_saved": tokens_saved}

    def tool_selection(self, available_tools: int, actually_needed: int) -> Dict:
        unused_tools = available_tools - actually_needed
        tokens_saved = unused_tools * 10
        self.rules_applied.append("Rule 7: Tool Selection")
        return {"available": available_tools, "to_use": actually_needed, "to_skip": unused_tools, "tokens_saved": tokens_saved}

    def memory_architecture(self) -> Dict:
        self.rules_applied.append("Rule 8: External Memory")
        return {"strategy": "Store in DB, fetch only needed rows", "tokens_saved": "~2000 per query"}

    def minimal_context(self, task: str, available_context: str, needed_context: str) -> Dict:
        total_tokens = len(available_context.split())
        minimal_tokens = len(needed_context.split())
        saved = total_tokens - minimal_tokens
        self.rules_applied.append("Rule 9: Minimal Context")
        return {"total_available": total_tokens, "actually_needed": minimal_tokens,
                "tokens_saved": saved, "percent_reduction": f"{(saved / total_tokens * 100):.0f}%" if total_tokens > 0 else "0%"}

    def batch_api_calls(self, individual_calls: int, batch_size: int = 10) -> Dict:
        overhead_per_call = 50
        individual_cost = individual_calls * overhead_per_call
        batched_cost = overhead_per_call + (individual_calls * 10)
        saved = individual_cost - batched_cost
        self.rules_applied.append("Rule 10: Batch API Calls")
        return {"individual_calls": individual_calls, "batched_calls": math.ceil(individual_calls / batch_size), "tokens_saved": saved}

    def streaming_output(self, response_size: str = "large") -> Dict:
        self.rules_applied.append("Rule 11: Streaming Output")
        return {"strategy": "Use streaming for long responses", "benefit": "Better UX, same token cost"}

    def clear_instructions(self, verbose_instruction: str, clear_instruction: str) -> Dict:
        verbose_tokens = len(verbose_instruction.split())
        clear_tokens = len(clear_instruction.split())
        overhead = 200
        self.rules_applied.append("Rule 12: Clear Instructions")
        return {"instruction_tokens_saved": verbose_tokens - clear_tokens,
                "potential_overhead_saved": overhead, "total_saved": (verbose_tokens - clear_tokens) + overhead}

    def structured_output(self, format: str = "json") -> Dict:
        self.rules_applied.append("Rule 13: Structured Output")
        return {"format": format, "efficiency": "23% mas conciso que prosa", "strategy": 'Always specify: "Respond as JSON"'}

    def distributed_execution(self, available_agents: List[str]) -> Dict:
        self.rules_applied.append("Rule 14: Distributed Execution")
        return {
            "agents_available": available_agents,
            "cost_distribution": {"OpenCode": "FREE", "Antigravity": "FREE", "QWEN": "FREE", "Claude": "EXPENSIVE"},
            "strategy": "Use cheap/free agents first, Claude only for high-value reasoning",
        }

    def token_monitoring(self, session_tokens_used: int, budget: int = 100000) -> Dict:
        percent_used = (session_tokens_used / budget) * 100
        remaining = budget - session_tokens_used
        self.rules_applied.append("Rule 15: Token Monitoring")
        return {"tokens_used": session_tokens_used, "budget": budget,
                "percent_used": f"{percent_used:.1f}%", "remaining": remaining,
                "alert": "REDUCE COSTS" if percent_used > 80 else "OK"}

    def generate_report(self, estimated_tokens: int = 0, estimated_cost: float = 0.0) -> str:
        rules_text = "\n".join([f"  - {rule}" for rule in self.rules_applied])
        return f"""Token Optimizer Report
=====================
Rules applied: {len(self.rules_applied)}
{rules_text}

Metrics:
  Tokens used: {estimated_tokens:,}
  Estimated cost: ${estimated_cost:.2f}

Recommendations:
  1. Select appropriate model per task
  2. Load only necessary MCPs and tools
  3. Distribute to free agents first (Ollama, local)
  4. Monitor token usage constantly
"""
