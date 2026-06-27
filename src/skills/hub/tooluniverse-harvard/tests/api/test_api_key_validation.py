#!/usr/bin/env python3
"""
Minimal test: validate API key during AgenticTool initialization.
- Success: prints OK and model info
- Failure: prints the error message (e.g., invalid/missing key or model not deployed)
"""

import os
import sys
import pytest

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


@pytest.mark.skipif(
    not os.getenv("AZURE_OPENAI_ENDPOINT") or not os.getenv("AZURE_OPENAI_API_KEY"),
    reason="Azure OpenAI credentials not available"
)
@pytest.mark.require_api_keys
def test_api_key_validation():
    """Test API key validation during AgenticTool initialization."""
    config = {
        "name": "api_key_validation_test",
        "description": "Minimal API key validation test",
        "type": "AgenticTool",
        "prompt": "Test: {q}",
        "input_arguments": ["q"],
        "parameter": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "input", "required": True}
            },
        },
        "return_schema": {"type": "string"},
        "model": "o4-mini-0416",
        "max_tokens": 1,
    }

    try:
        tool = AgenticTool(config)
        result = tool.run({"q": "test"})
        print(f"✅ API key validation successful: {result}")
        
        # Check if result is a dictionary with success field
        if isinstance(result, dict):
            assert result.get("success", False), "Expected successful result"
            assert "result" in result, "Expected 'result' field in response"
            print(f"✅ API response: {result.get('result', 'No result')}")
        else:
            assert isinstance(result, str), "Expected string or dict result"
            
    except Exception as e:
        print(f"❌ API key validation failed: {e}")
        pytest.fail(f"API key validation failed: {e}")


def main() -> None:
    config = {
        "name": "api_key_validation_test",
        "description": "Minimal API key validation test",
        "type": "AgenticTool",
        "prompt": "Test: {q}",
        "input_arguments": ["q"],
        "parameter": {
            "type": "object",
            "properties": {
                "q": {
                    "type": "string",
                    "description": "placeholder",
                    "required": True,
                }
            },
            "required": ["q"],
        },
        "configs": {
            "api_type": "CHATGPT",  # or "GEMINI" if you prefer
            "model_id": "gpt-4o-1120",  # requested model to test
            "validate_api_key": True,  # this triggers validation during init
            "temperature": 0.0,
            "max_new_tokens": 1,
        },
    }

    print("Running minimal API key validation test...")
    try:
        tool = AgenticTool(config)
        info = tool.get_model_info()
        print("OK: initialization succeeded and API key validated.")
        print(f"Model info: {info}")
    except Exception as e:
        print("ERROR: initialization failed during API key validation.")
        print(f"Reason: {e}")


if __name__ == "__main__":
    main()
