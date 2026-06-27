#!/usr/bin/env python3
"""
Simple Test for Human Expert System
"""

from tooluniverse import ToolUniverse

tooluni = ToolUniverse()
tooluni.load_tools()

# Submit question to expert
result = tooluni.run(
    {
        "name": "expert_consult_human_expert",
        "arguments": {
            "question": "What is the recommended dosage of aspirin for elderly patients?",
            "specialty": "cardiology",
            "priority": "high",  # normal, high, urgent
        },
    }
)
print("Request submitted. Result:")
print(result)
