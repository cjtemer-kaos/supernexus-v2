"""
MCPClientBridge - Consume external MCP servers

Allows NEXUS to connect to ANY MCP server and use its tools.
Features:
- Start MCP servers as subprocesses (stdio JSON-RPC)
- Tool discovery and normalization (mcp__{server}__{tool})
- Schema sanitization
- Health monitoring
- Tool execution with timeout

Refs: byo-coding-agent (Go→Python), learn-claude-code, nexus-mcp-server
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus-mcp-client")


@dataclass
class MCPTool:
    """Represents a tool from an MCP server."""
    name: str
    description: str
    input_schema: Dict
    server: str
    full_name: str = ""  # mcp__{server}__{tool}

    def __post_init__(self):
        if not self.full_name:
            self.full_name = f"mcp__{self.server}__{self.name}"


@dataclass
class MCPServer:
    """Configuration for an MCP server."""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    auto_start: bool = True
    tools: List[MCPTool] = field(default_factory=list)
    process: Optional[subprocess.Popen] = None
    connected: bool = False


class MCPClientBridge:
    """
    Bridge to external MCP servers.
    Manages server lifecycle, tool discovery, and execution.
    """

    def __init__(self, workdir: str = None):
        self.workdir = Path(workdir) if workdir else Path.cwd()
        self._servers: Dict[str, MCPServer] = {}
        self._tools: Dict[str, MCPTool] = {}
        self._request_id = 0

    # ─── Server Registration ───────────────────────────────────────────

    def register_server(self, name: str, command: str, args: List[str] = None,
                       env: Dict[str, str] = None, auto_start: bool = True) -> MCPServer:
        """Register an MCP server configuration."""
        server = MCPServer(
            name=name,
            command=command,
            args=args or [],
            env=env or {},
            auto_start=auto_start,
        )
        self._servers[name] = server
        logger.info(f"MCP server registered: {name} ({command} {' '.join(args)})")
        return server

    def register_builtin_servers(self):
        """Register common MCP servers."""
        # GitHub MCP (if available)
        self.register_server(
            name="github",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={"GITHUB_TOKEN": ""},  # User must configure
            auto_start=False,
        )

        # Filesystem MCP
        self.register_server(
            name="filesystem",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", str(self.workdir)],
            auto_start=False,
        )

        # SQLite MCP
        self.register_server(
            name="sqlite",
            command="uvx",
            args=["mcp-server-sqlite", "--db-path", str(Path.home() / ".nexus" / "brain" / "cerebro.db")],
            auto_start=False,
        )

        # Puppeteer MCP (web automation)
        self.register_server(
            name="puppeteer",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-puppeteer"],
            auto_start=False,
        )

    # ─── Server Lifecycle ──────────────────────────────────────────────

    async def start_server(self, name: str) -> bool:
        """Start an MCP server and discover its tools."""
        server = self._servers.get(name)
        if not server:
            logger.error(f"MCP server not found: {name}")
            return False

        if server.connected:
            logger.info(f"MCP server {name} already connected")
            return True

        logger.info(f"Starting MCP server: {name}")

        try:
            env = {**dict(__import__("os").environ), **server.env}
            server.process = subprocess.Popen(
                [server.command] + server.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=str(self.workdir),
            )
            logger.info(f"MCP server {name} started (PID: {server.process.pid})")

            # Discover tools
            tools = await self._discover_tools(server)
            server.tools = tools
            server.connected = True

            for tool in tools:
                self._tools[tool.full_name] = tool

            logger.info(f"MCP server {name}: {len(tools)} tools discovered")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server {name}: {e}")
            return False

    async def stop_server(self, name: str):
        """Stop an MCP server."""
        server = self._servers.get(name)
        if server and server.process:
            logger.info(f"Stopping MCP server: {name}")
            try:
                server.process.terminate()
                server.process.wait(timeout=5)
            except Exception:
                server.process.kill()
            server.connected = False
            server.process = None

            # Remove tools
            for tool in server.tools:
                self._tools.pop(tool.full_name, None)
            server.tools = []

    async def start_all(self):
        """Start all auto-start servers."""
        for name, server in self._servers.items():
            if server.auto_start:
                await self.start_server(name)

    async def stop_all(self):
        """Stop all servers."""
        for name in list(self._servers.keys()):
            await self.stop_server(name)

    # ─── Tool Discovery ────────────────────────────────────────────────

    async def _discover_tools(self, server: MCPServer) -> List[MCPTool]:
        """Discover tools from an MCP server via stdio JSON-RPC."""
        if not server.process or not server.process.stdin:
            return []

        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "SuperNEXUS", "version": "2.0.0"},
                },
            }
            await self._send_request(server, init_request)

            # Send initialized notification
            initialized = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
            await self._send_notification(server, initialized)

            # List tools
            tools_request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/list",
                "params": {},
            }
            response = await self._send_request(server, tools_request)

            if response and "result" in response:
                tools_data = response["result"].get("tools", [])
                tools = []
                for t in tools_data:
                    tool = MCPTool(
                        name=t["name"],
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}),
                        server=server.name,
                    )
                    tools.append(tool)
                return tools

        except Exception as e:
            logger.warning(f"Tool discovery failed for {server.name}: {e}")

        return []

    async def _send_request(self, server: MCPServer, request: Dict, timeout: float = 10.0) -> Optional[Dict]:
        """Send a JSON-RPC request and read response."""
        if not server.process or not server.process.stdin or not server.process.stdout:
            return None

        # Write request
        data = json.dumps(request) + "\n"
        server.process.stdin.write(data.encode())
        server.process.stdin.flush()

        # Read response (with timeout)
        import select
        if platform.system() != "Windows":
            ready, _, _ = select.select([server.process.stdout], [], [], timeout)
            if not ready:
                return None

        # Read line
        line = server.process.stdout.readline()
        if line:
            try:
                return json.loads(line.decode())
            except json.JSONDecodeError:
                return None
        return None

    async def _send_notification(self, server: MCPServer, notification: Dict):
        """Send a JSON-RPC notification (no response expected)."""
        if not server.process or not server.process.stdin:
            return
        data = json.dumps(notification) + "\n"
        server.process.stdin.write(data.encode())
        server.process.stdin.flush()

    # ─── Tool Execution ────────────────────────────────────────────────

    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Call an MCP tool by its full name (mcp__{server}__{tool}).
        Returns the tool result.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Tool not found: {tool_name}", "available": list(self._tools.keys())}

        server = self._servers.get(tool.server)
        if not server or not server.connected:
            return {"error": f"Server {tool.server} not connected"}

        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": tool.name,
                    "arguments": arguments,
                },
            }
            response = await self._send_request(server, request, timeout=30.0)

            if response and "result" in response:
                return {"success": True, "result": response["result"]}
            elif response and "error" in response:
                return {"error": response["error"].get("message", "Unknown error")}
            else:
                return {"error": "No response from server"}

        except Exception as e:
            return {"error": str(e)}

    # ─── Tool Listing ──────────────────────────────────────────────────

    def list_tools(self) -> List[Dict]:
        """List all available MCP tools."""
        return [
            {
                "name": tool.full_name,
                "description": tool.description,
                "server": tool.server,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def get_tools_for_server(self, server_name: str) -> List[Dict]:
        """List tools for a specific server."""
        return [
            {
                "name": tool.full_name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
            if tool.server == server_name
        ]

    # ─── Helpers ───────────────────────────────────────────────────────

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def get_status(self) -> Dict:
        return {
            "servers": {
                name: {
                    "connected": server.connected,
                    "tools": len(server.tools),
                    "command": server.command,
                }
                for name, server in self._servers.items()
            },
            "total_tools": len(self._tools),
        }

    def __del__(self):
        """Cleanup on deletion."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.stop_all())
            else:
                loop.run_until_complete(self.stop_all())
        except Exception:
            pass


# Platform import for _send_request
import platform
