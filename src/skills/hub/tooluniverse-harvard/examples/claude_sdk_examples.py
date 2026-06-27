import asyncio
import os
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query
from dotenv import load_dotenv

load_dotenv()


async def delegate_task(
    prompt: str,
    append_system_prompt: str,
):
    """Delegate a task to an expert
    Args:
        prompt: The prompt describing the task to delegate
        append_system_prompt: The system prompt describing the expert
    Returns:
        The result of the delegation
    """
    # Create sandbox directory if it doesn't exist
    sandbox_dir = Path(__file__).parent / "sandbox"
    sandbox_dir.mkdir(exist_ok=True)
    cwd = str(sandbox_dir)

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": append_system_prompt,
            },  # Use the preset
            cwd=cwd,
            permission_mode="bypassPermissions",
            mcp_servers={
                "tooluniverse": {
                    "type": "stdio",
                    "command": "uv",
                    "args": [
                        "run",
                        "tooluniverse-smcp-stdio",
                    ],
                    "env": {},
                },
            },
        ),
    ):
        # Print all message types to see tool usage
        message_type = type(message).__name__
        print(f"\n--- Message Type: {message_type} ---")

        # Check for tool use messages
        if message_type == "ToolUseMessage":
            print(f"Tool Name: {message.name}")
            print(f"Tool Input: {message.input}")
        elif message_type == "ToolResultMessage":
            print(f"Tool: {message.tool_use_id}")
            result_preview = (
                str(message.content)[:200]
                if hasattr(message, "content")
                else str(message)[:200]
            )
            print(f"Result: {result_preview}...")
        elif message_type == "TextMessage":
            text_preview = (
                str(message.text)[:200]
                if hasattr(message, "text")
                else str(message)[:200]
            )
            print(f"Text: {text_preview}...")
        elif message_type == "ResultMessage":
            return {
                "status": "success",
                "result": message.result,
            }
        else:
            # Print any other message types for debugging
            print(f"Message: {message}")


if __name__ == "__main__":
    # result = asyncio.run(conduct_research("What is the capital of France?"))
    # print(result)
    result = asyncio.run(
        delegate_task(
            "What tools do you have available? Return a list of all available tool names",
            "You are a helpful assistant",
        )
    )
    print(result)
