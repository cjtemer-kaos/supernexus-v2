#!/usr/bin/env python3
"""
Simple test for disease-target score extraction tools.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tooluniverse import ToolUniverse  # noqa: E402


def test_disease_target_score_tools():
    """Test the disease-target score extraction tools"""
    print("Testing Disease-Target Score Tools...")

    # Initialize ToolUniverse and load all tools
    engine = ToolUniverse()
    engine.load_tools()

    # Test both generic and specific tools
    tests = [
        (
            "generic tool",
            "disease_target_score",
            {"efoId": "EFO_0000339", "datasourceId": "impc"},
        ),
        (
            "ChEMBL-specific tool",
            "chembl_disease_target_score",
            {"efoId": "EFO_0000339"},
        ),
    ]

    for name, tool_name, args in tests:
        print(f"Testing {name}...")
        result = engine.run_one_function({"name": tool_name, "arguments": args})
        print(f"\033[92m{result}\033[0m")
        assert (
            result and result.get("total_targets_with_scores", 0) > 0
        ), f"{name} failed"
        print(f"✅ Found {result['total_targets_with_scores']} targets")

    print("🎉 All tests passed!")
    return True


if __name__ == "__main__":
    try:
        test_disease_target_score_tools()
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")
        sys.exit(1)
