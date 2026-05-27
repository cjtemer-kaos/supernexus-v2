#!/usr/bin/env python3
"""
Batch test: AgenticTool with multiple Azure OpenAI deployments.
- Validates API key during initialization
- Performs a tiny run call per model (1 token)
"""

import os
import sys
import pytest
from typing import List

# Ensure src/ is importable
CURRENT_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.join(CURRENT_DIR, "..", "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

try:
    from tooluniverse.agentic_tool import AgenticTool  # type: ignore
except ImportError:
    # Fallback for when running from different directory
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from tooluniverse.agentic_tool import AgenticTool  # type: ignore

# Chat-capable deployment IDs to test (skip embeddings)
MODELS: List[str] = [
    "gpt-4.1",
    "gpt-4.1-mini", 
    "gpt-4.1-nano",
    "gpt-4o-1120",
    "gpt-4o-0806",
    "gpt-4o-mini-0718",
    "o4-mini-0416",
    "o3-mini-0131",
]


@pytest.fixture(params=MODELS)
def model_id(request):
    """Fixture providing model IDs for parameterized testing."""
    return request.param


@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="Azure OpenAI credentials not available"
)
@pytest.mark.require_api_keys
def test_model(model_id: str) -> None:
    print(f"\n=== Testing model: {model_id} ===")
    config = {
        "name": f"agentic_test_{model_id}",
        "description": "AgenticTool model validation",
        "type": "AgenticTool",
        "prompt": "Echo: {q}",
        "input_arguments": ["q"],
        "parameter": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "input", "required": True}
            },
            "required": ["q"],
        },
        "configs": {
            "api_type": "CHATGPT",
            "model_id": model_id,
            "validate_api_key": True,
            "temperature": 0.0,
            "max_new_tokens": 1,
            "return_json": False,
            "return_metadata": False,
        },
    }

    try:
        tool = AgenticTool(config)
        print("- Init: OK (API key validated)")
    except Exception as e:
        print(f"- Init: FAIL -> {e}")
        return

    try:
        out = tool.run({"q": "ping"})
        ok = isinstance(out, (str, dict))
        output_str = str(out)[:120].replace('\n', ' ')
        print(f"- Run : {'OK' if ok else 'WARN'} -> {output_str}")
    except Exception as e:
        print(f"- Run : FAIL -> {e}")


def main() -> None:
    print("Azure endpoint:", os.getenv("AZURE_OPENAI_ENDPOINT"))
    print("Using per-model versions:")
    print(os.getenv("AZURE_OPENAI_API_VERSION_BY_MODEL", "<none>"))

    for m in MODELS:
        test_model(m)


if __name__ == "__main__":
    main()
