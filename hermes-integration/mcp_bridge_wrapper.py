"""
Wrapper para el MCP Bridge Server de SuperNEXUS
Ejecuta el servidor MCP con el path correcto para Hermes.

Uso:
  python mcp_bridge_wrapper.py
  
Este wrapper es lo que Hermes ejecuta como subprocess MCP.
"""
import os
import sys

# Add project root to path (same as start_server.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Windows: use SelectorEventLoop for stability
if sys.platform == "win32":
    asyncio_module = __import__("asyncio")
    asyncio_module.set_event_loop_policy(asyncio_module.WindowsSelectorEventLoopPolicy())

# Import and run the MCP bridge server
from src.bridges.mcp_bridge_server import mcp

if __name__ == "__main__":
    mcp.run()
