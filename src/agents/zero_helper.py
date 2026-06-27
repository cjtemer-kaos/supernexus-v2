"""
Agent Zero helper - runs INSIDE the Docker container.
Import Agent Zero directly and communicate.
Usage: docker exec <container> /opt/venv-a0/bin/python /zero_helper.py "prompt here"
"""
import sys

sys.path.insert(0, '/a0')

# Initialize Agent Zero runtime
from helpers import runtime, dotenv
runtime.initialize()
runtime.args["dockerized"] = "true"
dotenv.load_dotenv(encoding="utf-8-sig")

# Import Agent Zero modules
from agent import AgentContext, UserMessage, AgentContextType
from initialize import initialize_agent

async def run_agent(prompt):
    config = initialize_agent()
    context = AgentContext(config=config, type=AgentContextType.USER)
    AgentContext.use(context.id)
    task = context.communicate(UserMessage(message=prompt))
    result = await task.result()
    AgentContext.remove(context.id)
    return str(result)

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    import asyncio
    result = asyncio.run(run_agent(prompt))
    print(result)
