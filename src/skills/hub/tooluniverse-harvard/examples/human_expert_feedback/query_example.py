#!/usr/bin/env python3
"""
Simple Test for Human Expert System
"""

import os
import json
# Set environment variable for MCP server URL
os.environ['EXPERT_FEEDBACK_MCP_SERVER_URL'] = 'localhost:9876'

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

print(result)
print(result['content'][0])
# print the result
print("=" * 60)
print("EXPERT CONSULTATION RESULT")
print("=" * 60)

data = json.loads(result['content'][0]['text'])

# Display basic info
print(f"Request ID: {data.get('request_id', 'N/A')}")
print(f"Expert: {data.get('expert_name', 'N/A')}")
print(f"Specialty: {data.get('specialty', 'N/A')}")
print(f"Priority: {data.get('priority', 'N/A')}")
print(f"Response Time: {data.get('response_time', 'N/A')}")
print(f"Status: {data.get('status', 'N/A')}")

print("\n" + "=" * 60)
print("EXPERT ADVICE:")
print("=" * 60)

# Display expert response
expert_response = data.get('expert_response', 'No response available')
print(expert_response)

print("\n" + "=" * 60)
print("CONSULTATION COMPLETED")
print("=" * 60)
