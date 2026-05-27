"""
RCON Client - Control de servidores Rust para SuperNEXUS v2
WebSocket RCON async con aiohttp
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Set

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Allowed RCON commands for Rust servers (allowlist)
ALLOWED_RCON_COMMANDS = {
    "player.list", "playerlist", "serverinfo", "status", "time", "save",
    "quit", "restart", "writecfg", "server.writecfg",
    "kick", "ban", "banid", "unban", "banlist",
    "ownerid", "owneridlist", "removeowner",
    "moderatorid", "moderatoridlist", "removemoderator",
    "teleport", "tp", "tpid",
    "say", "server.say",
    "spawn", "give", "inventory.give",
    "entity.count", "entity.list",
    "global.kill", "global.respawn",
    "server.pve", "server.maxplayers",
    "server.description", "server.hostname",
    "weather", "env.time",
    "chat.say",
}

# Dangerous patterns that should never be allowed
DANGEROUS_RCON_PATTERNS = [
    r"(?i)(?:\bexec\b|\bload\b|\bimport\b|\brequire\b)",  # Code execution
    r"(?i)(?:\bshell\b|\bcmd\b|\bpowershell\b|\bbash\b)",  # Shell access
    r"(?i)(?:\bwrite\s+file\b|\bfile\.write\b|\bsave\s+file\b)",  # File writes
    r"(?i)(?:\bdelete\b|\bremove\s+server\b|\bdrop\s+table\b)",  # Destructive
    r"(?i)(?:\bnet\.write\b|\bhttp\b|\burl\b|\bdownload\b)",  # Network abuse
    r";\s*\w+",  # Command chaining
    r"\|\s*\w+",  # Pipe to other commands
]


def validate_rcon_command(command: str) -> tuple:
    """
    Valida un comando RCON contra allowlist y patrones peligrosos.
    
    Returns:
        (is_valid: bool, reason: str)
    """
    if not command or not command.strip():
        return False, "Empty command"

    cmd_stripped = command.strip().lower()

    # Check dangerous patterns first
    for pattern in DANGEROUS_RCON_PATTERNS:
        if re.search(pattern, command):
            return False, f"Dangerous pattern detected: {pattern}"

    # Extract base command (first word or word.word)
    base_cmd = cmd_stripped.split()[0] if cmd_stripped.split() else ""

    # Check allowlist
    if base_cmd in ALLOWED_RCON_COMMANDS:
        return True, ""

    # Allow commands with arguments (e.g., "kick playername reason")
    for allowed in ALLOWED_RCON_COMMANDS:
        if base_cmd == allowed or cmd_stripped.startswith(allowed + " "):
            return True, ""

    # Unknown command - reject by default
    return False, f"Command '{base_cmd}' not in allowed list"


class RustServerController:
    """Control de servidor Rust via WebSocket RCON"""

    def __init__(self):
        self.ws = None
        self.connected = False
        self.server_info = {}
        self.callbacks = []
        self.last_response = None
        self.message_id = 0
        self.password = ""
        self.server_ip = ""
        self.server_port = 0
        self._response_events: Dict[int, asyncio.Event] = {}
        self._response_data: Dict[int, str] = {}
        self._listener_task = None

    async def connect(self, ip: str, port: int = 28016, password: str = "") -> bool:
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets no disponible. pip install websockets")
            return False

        try:
            url = f"ws://{ip}:{port}"
            self.ws = await websockets.connect(url)
            self.connected = True
            self.password = password
            self.server_ip = ip
            self.server_port = port
            logger.info(f"Connected to {ip}:{port}")

            if password:
                await self._send_auth()

            self._listener_task = asyncio.create_task(self._listen())
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    async def _send_auth(self):
        await self._send_raw({"Identifier": -1, "Message": self.password, "Type": "Auth"})

    async def _send_raw(self, data: dict):
        if self.ws:
            await self.ws.send(json.dumps(data))

    async def _listen(self):
        async for message in self.ws:
            try:
                data = json.loads(message)
                if data.get("Identifier") == -1:
                    logger.info(f"AUTH: {data.get('Message')}")
                else:
                    msg_id = data.get("Identifier", 0)
                    self.last_response = data.get("Message", "")
                    if msg_id in self._response_events:
                        self._response_data[msg_id] = self.last_response
                        self._response_events[msg_id].set()
                    for callback in self.callbacks:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(data)
                        else:
                            callback(data)
            except json.JSONDecodeError:
                pass

    async def send(self, command: str, timeout: float = 5.0, skip_validation: bool = False) -> Optional[str]:
        if not skip_validation:
            is_valid, reason = validate_rcon_command(command)
            if not is_valid:
                logger.warning(f"RCON command rejected: {command} - {reason}")
                return f"Command rejected: {reason}"

        self.message_id += 1
        event = asyncio.Event()
        self._response_events[self.message_id] = event

        data = {"Identifier": self.message_id, "Message": command, "Type": "ExecuteServerCommand"}
        await self._send_raw(data)

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return self._response_data.pop(self.message_id, self.last_response)
        except asyncio.TimeoutError:
            logger.warning(f"RCON timeout for command: {command}")
            return None
        finally:
            self._response_events.pop(self.message_id, None)

    def on_message(self, callback):
        self.callbacks.append(callback)

    async def disconnect(self):
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self.ws:
            await self.ws.close()
        self.connected = False

    async def get_players(self) -> List[Dict]:
        response = await self.send("player.list")
        if response:
            return self._parse_player_list(response)
        return []

    def _parse_player_list(self, text: str) -> List[Dict]:
        players = []
        for line in text.split('\n'):
            if line.strip():
                players.append({"name": line.strip()})
        return players

    async def get_info(self) -> Dict:
        info = {}
        resp = await self.send("serverinfo")
        if resp:
            for line in resp.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    info[key.strip()] = val.strip()
        return info

    async def add_owner(self, steamid: str, nickname: str, reason: str = "") -> bool:
        cmd = f'ownerid "{steamid}" "{nickname}" "{reason}"'
        resp = await self.send(cmd)
        return "added" in (resp or "").lower()

    async def add_moderator(self, steamid: str, nickname: str) -> bool:
        cmd = f'moderatorid "{steamid}" "{nickname}"'
        resp = await self.send(cmd)
        return "added" in (resp or "").lower()

    async def save(self) -> bool:
        resp = await self.send("save")
        return resp is not None

    async def kick_player(self, player_name: str, reason: str = "Kicked") -> bool:
        cmd = f'kick "{player_name}" "{reason}"'
        resp = await self.send(cmd)
        return resp is not None

    async def ban_player(self, player_name: str) -> bool:
        cmd = f'ban "{player_name}"'
        resp = await self.send(cmd)
        return resp is not None

    async def teleport_to_player(self, player_name: str) -> bool:
        cmd = f'tp "{player_name}"'
        resp = await self.send(cmd)
        return resp is not None

    def get_status(self) -> Dict:
        return {
            "connected": self.connected,
            "server": f"{self.server_ip}:{self.server_port}",
        }


class RustServerManager:
    """Gestor multiple de servidores Rust"""

    def __init__(self, config_file: str = "rust_servers.json"):
        self.config_file = config_file
        self.servers = {}
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_file, 'r') as f:
                self.servers = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.servers = {}

    def _save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.servers, f, indent=2)

    def add_server(self, name: str, ip: str, port: int = 28016, password: str = "") -> bool:
        self.servers[name] = {"ip": ip, "port": port, "password": password}
        self._save_config()
        return True

    def remove_server(self, name: str) -> bool:
        if name in self.servers:
            del self.servers[name]
            self._save_config()
            return True
        return False

    def list_servers(self) -> List[str]:
        return list(self.servers.keys())

    async def connect(self, name: str) -> Optional[RustServerController]:
        if name not in self.servers:
            return None
        config = self.servers[name]
        controller = RustServerController()
        if await controller.connect(config["ip"], config["port"], config["password"]):
            return controller
        return None

    def get_quick_commands(self) -> List[Dict]:
        return [
            {"name": "Lista Jugadores", "cmd": "player.list"},
            {"name": "Info Servidor", "cmd": "serverinfo"},
            {"name": "Guardar", "cmd": "save"},
            {"name": "Estado", "cmd": "status"},
            {"name": "Tiempo", "cmd": "time"},
        ]
