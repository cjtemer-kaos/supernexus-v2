"""
SuperNEXUS Sovereign - Cerebro Unificado MCP

Hub central de comunicacion en tiempo real entre aplicaciones:
Claude Desktop, Claude Code, Gemini, agentes, remote_node, etc.

Capacidades:
- Mensajeria en tiempo real entre apps (tablero compartido)
- Memoria compartida (Cerebro adaptativo)
- Control de nodos remotos (remote_node, etc.)

Fixes aplicados (2026-05-17):
- WAL mode + busy_timeout para concurrencia (Claude + Antigravity)
- Indices para performance (174K+ mensajes)
- SQL injection fix (whitelist en lugar de f-strings)
- httpx moved to top-level import
- import re removed from loop
- BRAIN_DIR Path mixing fixed
- _*_impl functions marked DEPRECATED (eliminar cuando server.py migre)
- Gestion de tareas entre agentes
- Estado del sistema completo
"""

import sys
import json
import os
import logging
import sqlite3
import re
import traceback
from typing import Optional
from datetime import datetime
from pathlib import Path

# Optimizacion: imports a top-level
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("nexus-sovereign")

# Cargar .env si existe para robustez en control de nodos
for p in [Path(__file__).resolve().parents[2] / ".env", Path.cwd() / ".env"]:
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception as e:
            logger.error(f"Error cargando .env desde {p}: {e}")

REMOTE_NODE_IP = os.environ.get("SUPER_NEXUS_REMOTE_NODE_IP", "")
NEXUS_HOME = os.environ.get("NEXUS_HOME", str(Path.home() / ".nexus"))
BRAIN_DIR = Path(os.environ.get("NEXUS_BRAIN", str(Path.home() / ".nexus" / "brain")))
BRAIN_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# Shared state: message board + brain DB
# ============================================================
_BOARD_DB = BRAIN_DIR / "message_board.db"
_BRAIN_DB = BRAIN_DIR / "cerebro.db"
_TASK_DIR = Path.home() / ".gemini" / "antigravity" / "scratch" / "Tasks"
_TASK_DIR.mkdir(parents=True, exist_ok=True)


def _get_board_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_BOARD_DB), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _get_brain_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_BRAIN_DB), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _init_board_db():
    """Inicializa la base de datos del tablero de mensajes compartido."""
    conn = sqlite3.connect(str(_BOARD_DB), timeout=30)
    c = conn.cursor()
    # Fix critico: WAL mode para concurrencia (identificado por Claude + Antigravity)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    c.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        sender TEXT NOT NULL,
        target TEXT DEFAULT '*',
        channel TEXT DEFAULT 'general',
        content TEXT NOT NULL,
        msg_type TEXT DEFAULT 'chat',
        metadata TEXT DEFAULT '{}'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS shared_memory (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_by TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""")
    # Indices para performance (174K+ mensajes)
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_target ON messages(target, channel, timestamp)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(msg_type, timestamp)")
    conn.commit()
    conn.close()

_init_board_db()


# ============================================================
# FastMCP Server
# ============================================================
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("nexus-sovereign")


# ---- MENSAJERIA EN TIEMPO REAL ----

@mcp.tool()
async def send_message(
    content: str,
    sender: str = "claude-code",
    target: str = "*",
    channel: str = "general",
    msg_type: str = "chat",
) -> str:
    """Send a message to the shared board. All connected apps (Claude Desktop, Claude Code, Gemini, agents) can read it. Use target='*' to broadcast, or a specific app name."""
    conn = _get_board_conn()
    c = conn.cursor()
    ts = datetime.now().isoformat()
    c.execute(
        "INSERT INTO messages (timestamp, sender, target, channel, content, msg_type) VALUES (?, ?, ?, ?, ?, ?)",
        (ts, sender, target, channel, content, msg_type),
    )
    msg_id = c.lastrowid
    conn.commit()
    conn.close()
    return json.dumps({"sent": True, "id": msg_id, "timestamp": ts}, indent=2)


@mcp.tool()
async def read_messages(
    channel: str = "general",
    limit: int = 20,
    since: str = "",
    sender: str = "",
) -> str:
    """Read messages from the shared board. Filter by channel, sender, or time. This is how apps communicate in real-time."""
    conn = _get_board_conn()
    c = conn.cursor()
    query = "SELECT id, timestamp, sender, target, channel, content, msg_type FROM messages WHERE channel = ?"
    params = [channel]
    if since:
        query += " AND timestamp > ?"
        params.append(since)
    if sender:
        query += " AND sender = ?"
        params.append(sender)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    messages = [
        {"id": r[0], "timestamp": r[1], "sender": r[2], "target": r[3],
         "channel": r[4], "content": r[5], "type": r[6]}
        for r in reversed(rows)
    ]
    return json.dumps({"messages": messages, "count": len(messages)}, indent=2, ensure_ascii=False)


# ---- MEMORIA COMPARTIDA (key-value rapido) ----

@mcp.tool()
async def memory_set(key: str, value: str, updated_by: str = "claude-code") -> str:
    """Set a shared memory value. Any app can read/write. Use for sharing state between Claude Desktop, Claude Code, agents, etc."""
    conn = _get_board_conn()
    c = conn.cursor()
    ts = datetime.now().isoformat()
    c.execute(
        "INSERT OR REPLACE INTO shared_memory (key, value, updated_by, updated_at) VALUES (?, ?, ?, ?)",
        (key, value, updated_by, ts),
    )
    conn.commit()
    conn.close()
    return json.dumps({"key": key, "set": True, "by": updated_by}, indent=2)


@mcp.tool()
async def memory_get(key: str = "", prefix: str = "") -> str:
    """Get shared memory value(s). Pass key for exact match, or prefix to list all keys starting with it. Omit both to list all."""
    conn = _get_board_conn()
    c = conn.cursor()
    if key:
        c.execute("SELECT key, value, updated_by, updated_at FROM shared_memory WHERE key = ?", (key,))
    elif prefix:
        c.execute("SELECT key, value, updated_by, updated_at FROM shared_memory WHERE key LIKE ?", (f"{prefix}%",))
    else:
        c.execute("SELECT key, value, updated_by, updated_at FROM shared_memory")
    rows = c.fetchall()
    conn.close()
    data = {r[0]: {"value": r[1], "by": r[2], "at": r[3]} for r in rows}
    return json.dumps(data, indent=2, ensure_ascii=False)


# ---- CEREBRO (memoria adaptativa de largo plazo) ----

@mcp.tool()
async def brain_remember(
    topic: str,
    content: str,
    source: str = "claude-code",
    importance: int = 5,
) -> str:
    """Store knowledge in the shared brain (long-term memory). The brain learns from all apps - patterns, preferences, facts."""
    conn = _get_brain_conn()
    c = conn.cursor()
    # Ensure tables exist
    c.execute("""CREATE TABLE IF NOT EXISTS conocimientos (
        id INTEGER PRIMARY KEY, tema TEXT, contenido TEXT,
        fuente TEXT, fecha TEXT, veces_revisado INTEGER DEFAULT 0,
        utilidad INTEGER DEFAULT 5, consolidado BOOLEAN DEFAULT 0)""")
    ts = datetime.now().isoformat()
    c.execute("SELECT id FROM conocimientos WHERE tema = ?", (topic,))
    if c.fetchone():
        c.execute(
            "UPDATE conocimientos SET contenido = ?, fuente = ?, fecha = ?, utilidad = ?, veces_revisado = veces_revisado + 1 WHERE tema = ?",
            (content, source, ts, importance, topic),
        )
        action = "updated"
    else:
        c.execute(
            "INSERT INTO conocimientos (tema, contenido, fuente, fecha, utilidad) VALUES (?, ?, ?, ?, ?)",
            (topic, content, source, ts, importance),
        )
        action = "created"
    conn.commit()
    conn.close()
    return json.dumps({"topic": topic, "action": action, "source": source}, indent=2)


@mcp.tool()
async def brain_recall(query: str = "", topic: str = "", limit: int = 10) -> str:
    """Recall knowledge from the shared brain. Search by topic or free-text query across all stored knowledge."""
    conn = _get_brain_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS conocimientos (
        id INTEGER PRIMARY KEY, tema TEXT, contenido TEXT,
        fuente TEXT, fecha TEXT, veces_revisado INTEGER DEFAULT 0,
        utilidad INTEGER DEFAULT 5, consolidado BOOLEAN DEFAULT 0)""")
    if topic:
        c.execute("SELECT tema, contenido, fuente, fecha, utilidad FROM conocimientos WHERE tema LIKE ? ORDER BY utilidad DESC LIMIT ?",
                  (f"%{topic}%", limit))
    elif query:
        c.execute("SELECT tema, contenido, fuente, fecha, utilidad FROM conocimientos WHERE tema LIKE ? OR contenido LIKE ? ORDER BY utilidad DESC LIMIT ?",
                  (f"%{query}%", f"%{query}%", limit))
    else:
        c.execute("SELECT tema, contenido, fuente, fecha, utilidad FROM conocimientos ORDER BY utilidad DESC, fecha DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    knowledge = [
        {"topic": r[0], "content": r[1], "source": r[2], "date": r[3], "importance": r[4]}
        for r in rows
    ]
    return json.dumps({"knowledge": knowledge, "count": len(knowledge)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def brain_stats() -> str:
    """Get unified brain statistics - memory usage, conversations, patterns, all connected state."""
    stats = {"brain_dir": str(BRAIN_DIR)}

    # Board stats
    try:
        conn = _get_board_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM messages")
        stats["total_messages"] = c.fetchone()[0]
        c.execute("SELECT DISTINCT sender FROM messages")
        stats["active_senders"] = [r[0] for r in c.fetchall()]
        c.execute("SELECT DISTINCT channel FROM messages")
        stats["channels"] = [r[0] for r in c.fetchall()]
        c.execute("SELECT COUNT(*) FROM shared_memory")
        stats["shared_memory_keys"] = c.fetchone()[0]
        conn.close()
    except Exception:
        stats["board"] = "not initialized"

    # Brain stats
    try:
        conn = sqlite3.connect(str(_BRAIN_DB), timeout=30)
        c = conn.cursor()
        c.execute("PRAGMA journal_mode=WAL")
        # Fix: whitelist en lugar de f-strings (SQL injection risk)
        VALID_TABLES = ["conocimientos", "conversaciones", "patrones", "memoria", "eventos"]
        for table in VALID_TABLES:
            try:
                c.execute("SELECT COUNT(*) FROM " + table)
                stats[table] = c.fetchone()[0]
            except Exception:
                stats[table] = 0
        conn.close()
    except Exception:
        stats["cerebro"] = "not initialized"

    return json.dumps(stats, indent=2, ensure_ascii=False)


def get_remote_node_ip() -> str:
    """Obtiene la IP del nodo remoto cargando el .env dinámicamente si es necesario."""
    for p in [Path(__file__).resolve().parents[2] / ".env", Path.cwd() / ".env"]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            os.environ[k.strip()] = v.strip()
            except Exception:
                pass
    return os.environ.get("SUPER_NEXUS_REMOTE_NODE_IP", "")


# ---- CONTROL DE NODOS ----

@mcp.tool()
async def execute_on_remote_node(command: str) -> str:
    """Execute a bash command on a remote node via HTTP. Use for server management, GPU tasks, and remote operations."""


async def execute_on_pc2(command: str) -> str:
    """Alias for execute_on_remote_node. Mantiene compatibilidad con server.py."""
    return await execute_on_remote_node(command)
    if not HTTPX_AVAILABLE:
        return json.dumps({"error": "httpx not installed"}, indent=2)
    remote_ip = get_remote_node_ip()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"http://{remote_ip}:9000/api/chat",
                json={"message": f"Ejecuta este comando en la terminal y devuelve solo el resultado: {command}"},
            )
            if r.status_code == 200:
                data = r.json()
                return json.dumps({
                    "command": command, "success": data.get("success", False),
                    "output": data.get("reply", ""), "model": data.get("model", ""),
                }, indent=2, ensure_ascii=False)
            return json.dumps({"error": f"HTTP {r.status_code}", "command": command}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "command": command, "hint": "Remote node may be offline"}, indent=2)


@mcp.tool()
async def list_nodes() -> str:
    """List all nodes in the NexusHive network with their status."""
    if not HTTPX_AVAILABLE:
        return json.dumps({"error": "httpx not installed"}, indent=2)
    remote_ip = get_remote_node_ip()
    nodes = {
        "pc1": {"name": "PC1 - Windows Main", "ip": "localhost", "status": "online",
                "capabilities": ["claude-code", "claude-desktop", "supernexus", "ollama"]},
        "remote_node": {"name": "remote_node - Linux GPU", "ip": remote_ip, "status": "unknown",
                "capabilities": ["gpu", "ollama", "ssh", "comfyui"]},
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"http://{remote_ip}:9000/api/status")
            nodes["remote_node"]["status"] = "online" if r.status_code == 200 else "degraded"
    except Exception:
        nodes["remote_node"]["status"] = "offline"
    return json.dumps(nodes, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_system_info(node_id: str = "pc1", info_type: str = "all") -> str:
    """Get system information from any node. info_type: gpu, cpu, memory, disk, ollama, all."""
    if node_id == "pc1":
        import platform
        info = {"node": "pc1", "os": platform.system(), "release": platform.release(),
                "machine": platform.machine(), "processor": platform.processor()}
        return json.dumps(info, indent=2, ensure_ascii=False)

    if node_id == "remote_node":
        remote_ip = get_remote_node_ip()
        cmd_map = {
            "gpu": "nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu --format=csv,noheader",
            "cpu": "lscpu | head -20", "memory": "free -h", "disk": "df -h /",
            "ollama": "curl -s http://localhost:11434/api/tags",
            "all": "echo '=== GPU ===' && nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo 'No GPU' && echo '=== MEM ===' && free -h && echo '=== DISK ===' && df -h /",
        }
        cmd = cmd_map.get(info_type, cmd_map["all"])
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post(f"http://{remote_ip}:9000/api/chat", json={"message": f"Ejecuta: {cmd}"})
                if r.status_code == 200:
                    return json.dumps({"node": node_id, "info_type": info_type,
                                       "output": r.json().get("reply", "")}, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "node": node_id}, indent=2)

    return json.dumps({"error": f"Node {node_id} not available"}, indent=2)


@mcp.tool()
async def execute_remote_task(node_id: str, task: str, timeout: int = 30) -> str:
    """Execute a task on a remote node via NexusHive."""
    if not HTTPX_AVAILABLE:
        return json.dumps({"error": "httpx not installed"}, indent=2)
    if node_id == "remote_node":
        remote_ip = get_remote_node_ip()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                r = await client.post(f"http://{remote_ip}:9000/api/chat", json={"message": task})
                if r.status_code == 200:
                    return json.dumps({"node": node_id, "task": task, "success": True,
                                       "output": r.json().get("reply", "")}, indent=2, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "node": node_id}, indent=2)
    return json.dumps({"error": f"Node {node_id} not reachable"}, indent=2)



# ---- TAREAS ENTRE AGENTES ----

@mcp.tool()
async def send_task_to_antigravity(task_description: str, priority: str = "medium") -> str:
    """Send a task to the Antigravity agent. Tasks are logged and processed asynchronously."""
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_file = _TASK_DIR / f"task_{task_id}.json"
    task_data = {"id": task_id, "description": task_description, "priority": priority,
                 "timestamp": datetime.now().isoformat(), "status": "pending"}
    task_file.write_text(json.dumps(task_data, indent=2, ensure_ascii=False))
    # Also post to the message board
    conn = _get_board_conn()
    c = conn.cursor()
    c.execute("INSERT INTO messages (timestamp, sender, target, channel, content, msg_type) VALUES (?, ?, ?, ?, ?, ?)",
              (datetime.now().isoformat(), "task-manager", "antigravity", "tasks", task_description, "task"))
    conn.commit()
    conn.close()
    return json.dumps({"status": "task_logged", "task_id": task_id, "priority": priority}, indent=2)


@mcp.tool()
async def nexus_status() -> str:
    """Get full SuperNEXUS system status - API server, nodes, brain, everything."""
    if not HTTPX_AVAILABLE:
        return json.dumps({"error": "httpx not installed"}, indent=2)
    status = {"timestamp": datetime.now().isoformat(), "nexus_home": NEXUS_HOME}

    # Check API server (port 9000)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://localhost:9000/api/status")
            if r.status_code == 200:
                status["api_server"] = "online"
                api_data = r.json()
                status["engines"] = api_data.get("engines", {})
                status["cerebro"] = api_data.get("cerebro", {})
                status["nexus_hive"] = api_data.get("nexus_hive", {})
            else:
                status["api_server"] = "error"
    except Exception:
        status["api_server"] = "offline"

    # Check remote_node
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"http://{remote_ip}:9000/api/status")
            status["remote_node"] = "online" if r.status_code == 200 else "degraded"
    except Exception:
        status["remote_node"] = "offline"

    # Check local Ollama
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                status["ollama_local"] = {"status": "online", "models": len(models)}
    except Exception:
        status["ollama_local"] = {"status": "offline"}

    return json.dumps(status, indent=2, ensure_ascii=False)


# ---- OPTIMIZACION DE TOKENS ----

@mcp.tool()
async def optimize_prompt(prompt: str) -> str:
    """Compress a prompt removing filler words, redundancies. Returns compressed version + savings percentage. Use before sending expensive API calls."""
    import re
    original_tokens = len(prompt.split())
    compressions = {
        r'\s+': ' ', r'(?i)please\s': '', r'(?i)thank you': 'thx',
        r'(?i)could you': 'can you', r'(?i)would you mind': 'can you',
        r'(?i)I would like': 'I need', r'(?i)In my opinion': 'IMO',
        r'(?i)basically': '', r'(?i)essentially': '', r'(?i)obviously': '',
        r'(?i)as I mentioned earlier': '', r'(?i)as mentioned before': '',
        r'(?i)it is important to note that': '', r'(?i)it should be noted that': '',
    }
    compressed = prompt
    for pattern, replacement in compressions.items():
        compressed = re.sub(pattern, replacement, compressed)
    compressed = re.sub(r' +', ' ', compressed).strip()
    compressed_tokens = len(compressed.split())
    reduction = ((original_tokens - compressed_tokens) / original_tokens * 100) if original_tokens > 0 else 0
    return json.dumps({
        "original_tokens": original_tokens,
        "compressed_tokens": compressed_tokens,
        "reduction_percent": round(reduction, 1),
        "compressed": compressed,
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def select_model(task_type: str, complexity: str = "medium") -> str:
    """Select the optimal model for a task based on type and complexity. Saves money by routing simple tasks to cheap models.
    task_type: simple, categorization, coding, analysis, design, research, reasoning, local
    complexity: low, medium, complex, deep"""
    models = {
        ("simple", "low"): {"model": "haiku", "cost": "$0.80/1M", "reason": "Simple task, cheapest model"},
        ("categorization", "low"): {"model": "haiku", "cost": "$0.80/1M", "reason": "Classification doesn't need big model"},
        ("coding", "medium"): {"model": "sonnet", "cost": "$3/1M", "reason": "Good balance for code"},
        ("coding", "complex"): {"model": "sonnet", "cost": "$3/1M", "reason": "Sonnet handles complex code well"},
        ("analysis", "medium"): {"model": "sonnet", "cost": "$3/1M", "reason": "Analysis needs reasoning"},
        ("design", "medium"): {"model": "sonnet", "cost": "$3/1M", "reason": "Creative + technical"},
        ("research", "deep"): {"model": "opus", "cost": "$15/1M", "reason": "Deep research needs max capability"},
        ("reasoning", "complex"): {"model": "opus", "cost": "$15/1M", "reason": "Complex reasoning"},
        ("local", "low"): {"model": "ollama/nemotron", "cost": "FREE", "reason": "Use local model, zero cost"},
        ("local", "medium"): {"model": "ollama/qwen2.5-coder:7b", "cost": "FREE", "reason": "Local coder, zero cost"},
    }
    key = (task_type, complexity)
    result = models.get(key, {"model": "sonnet", "cost": "$3/1M", "reason": "Default balanced choice"})
    result["task_type"] = task_type
    result["complexity"] = complexity
    result["tip"] = "Use 'local' task_type for FREE execution via Ollama"
    return json.dumps(result, indent=2)


@mcp.tool()
async def token_report() -> str:
    """Get token optimization tips and the 9 techniques for 90% reduction. Use this to learn how to save tokens across all apps."""
    return json.dumps({
        "techniques": [
            {"name": "Context Window Awareness", "savings": "20-30%", "how": "Put critical instructions at TOP and BOTTOM of prompt, not middle"},
            {"name": "Prompt Compression", "savings": "10-15%", "how": "Remove filler words (basically, essentially, please). Use optimize_prompt tool"},
            {"name": "Structural Format", "savings": "20-30%", "how": "Use TASK/CONTEXT/CONSTRAINTS/OUTPUT format instead of prose"},
            {"name": "Incremental Execution", "savings": "30-40%", "how": "Do one step -> validate -> next. Fail fast, don't waste tokens"},
            {"name": "Tool Prioritization", "savings": "15-25%", "how": "grep -> read_specific_lines -> read_full. Cheapest tool first"},
            {"name": "Output Format", "savings": "30-50%", "how": "Always ask for JSON output, not prose. 23% more concise"},
            {"name": "Context Reuse", "savings": "70-90%", "how": "Load context once via memory_set, reuse N times via memory_get"},
            {"name": "Selective Memory", "savings": "95%+", "how": "Use brain_recall with specific topic, don't load all memory"},
            {"name": "No Repetition", "savings": "75%", "how": "State rules once in system prompt. Never repeat in messages"},
        ],
        "model_routing": {
            "FREE": ["ollama/nemotron", "ollama/qwen-coder", "OpenCode", "Antigravity"],
            "CHEAP": ["haiku ($0.80/1M)"],
            "BALANCED": ["sonnet ($3/1M)"],
            "EXPENSIVE": ["opus ($15/1M) - only for deep reasoning"],
        },
        "golden_rule": "Use free/local agents first. Claude only for high-value reasoning.",
    }, indent=2)


# ---- MONITOREO DE SISTEMA ----

@mcp.tool()
async def system_resources() -> str:
    """Check CPU, RAM, disk usage on PC1. Use before running heavy tasks to know if system can handle it."""
    stats = {"node": "pc1"}
    try:
        import psutil
        stats["cpu_percent"] = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        stats["ram_percent"] = mem.percent
        stats["ram_used_gb"] = round(mem.used / (1024**3), 1)
        stats["ram_total_gb"] = round(mem.total / (1024**3), 1)
        try:
            disk = psutil.disk_usage("D:\\")
            stats["disk_d_percent"] = disk.percent
            stats["disk_d_free_gb"] = round(disk.free / (1024**3), 1)
        except Exception:
            pass
        try:
            disk_c = psutil.disk_usage("C:\\")
            stats["disk_c_percent"] = disk_c.percent
            stats["disk_c_free_gb"] = round(disk_c.free / (1024**3), 1)
        except Exception:
            pass
        stats["safe_to_run_heavy"] = stats["cpu_percent"] < 75 and stats["ram_percent"] < 80
    except ImportError:
        stats["error"] = "psutil not installed"
    return json.dumps(stats, indent=2)


# ============================================================
_SKILLS_BASE = Path(NEXUS_HOME) / "distros" / "NEXUS_CORE_windows" / "01_CORE" / "2_HABILIDADES" / "skills"
_SKILLS_CATALOG = Path(NEXUS_HOME) / "distros" / "NEXUS_CORE_windows" / "01_CORE" / "2_HABILIDADES" / "SANTOS_SKILLS_CATALOG.md"
_CATALOG_CACHE = None


def _get_catalog():
    """Parse and cache the skills catalog for fast searching."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    _CATALOG_CACHE = []
    if not _SKILLS_CATALOG.exists():
        # Fallback: list directories
        if _SKILLS_BASE.exists():
            for d in sorted(_SKILLS_BASE.iterdir()):
                if d.is_dir():
                    _CATALOG_CACHE.append({"name": d.name, "description": "", "tags": "", "category": "unknown"})
        return _CATALOG_CACHE

    current_category = ""
    for line in _SKILLS_CATALOG.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            m = re.match(r"## ([\w\s-]+) \((\d+)\)", line)
            if m:
                current_category = m.group(1).strip()
        elif line.startswith("| `"):
            parts = line.split("|")
            if len(parts) >= 5:
                name = parts[1].strip().strip("`")
                desc = parts[2].strip()
                tags = parts[3].strip()
                _CATALOG_CACHE.append({"name": name, "description": desc, "tags": tags, "category": current_category})
    return _CATALOG_CACHE


@mcp.tool()
async def list_skills(query: str = "", category: str = "", limit: int = 30) -> str:
    """Search the 1,441+ skill catalog. Use query to filter by name/tags/description. Categories: architecture, business, data-ai, development, general, infrastructure, security, testing, workflow. Returns names to use with load_skill."""
    catalog = _get_catalog()
    results = []
    q = query.lower()

    for skill in catalog:
        if category and category.lower() not in skill["category"].lower():
            continue
        if q:
            searchable = f"{skill['name']} {skill['description']} {skill['tags']}".lower()
            if not all(word in searchable for word in q.split()):
                continue
        results.append({
            "name": skill["name"],
            "description": skill["description"][:150],
            "category": skill["category"]
        })
        if len(results) >= limit:
            break

    return json.dumps({
        "results": results,
        "count": len(results),
        "total_catalog": len(catalog),
        "hint": "Use load_skill(skill_name) to get full content"
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def load_skill(name: str) -> str:
    """Load the full content of a skill by name. Returns the complete SKILL.md with instructions, patterns, and knowledge."""
    skill_path = _SKILLS_BASE / name / "SKILL.md"

    if not skill_path.exists():
        # Fallback: search in src/skills as .py
        py_path = Path(NEXUS_HOME) / "proyectos" / "supernexus-v2" / "src" / "skills" / f"{name}.py"
        if py_path.exists():
            content = py_path.read_text(encoding="utf-8")
            return json.dumps({"name": name, "type": "python_skill", "content": content[:8000]}, ensure_ascii=False)
        return json.dumps({"error": f"Skill '{name}' not found", "searched": [str(skill_path), str(py_path)]})

    content = skill_path.read_text(encoding="utf-8")
    # Truncate if too large (some skills are 400KB+)
    if len(content) > 12000:
        content = content[:12000] + f"\n\n... [TRUNCATED - full skill is {len(content)} chars. Use load_skill_section for specific parts]"

    return json.dumps({"name": name, "type": "skill_md", "chars": len(content), "content": content}, ensure_ascii=False)


@mcp.tool()
async def load_skill_section(name: str, offset: int = 0, length: int = 8000) -> str:
    """Load a specific section of a large skill. Use offset and length to paginate through skills larger than 12000 bytes."""
    skill_path = _SKILLS_BASE / name / "SKILL.md"

    if not skill_path.exists():
        return json.dumps({"error": f"Skill '{name}' not found"})

    content = skill_path.read_text(encoding="utf-8")
    section = content[offset:offset + length]
    return json.dumps({
        "name": name,
        "total_chars": len(content),
        "offset": offset,
        "length": len(section),
        "has_more": offset + length < len(content),
        "content": section
    }, ensure_ascii=False)


# ---- MEMORIA BLAST (findings, decisions, cloud) ----

_FINDINGS = BRAIN_DIR / "findings.md"
_DECISIONS = BRAIN_DIR / "decisions.md"
_CLOUD = BRAIN_DIR / "cloud.md"

# Agent permissions (Suprawall)
_AGENT_PERMS = {
    "claude-code": {"execute": True, "read_all": True, "write_memory": True, "delegate": True, "max_tasks": 5},
    "opencode": {"execute": True, "read_all": True, "write_memory": True, "delegate": False, "max_tasks": 3},
    "antigravity": {"execute": True, "read_all": True, "write_memory": True, "delegate": True, "max_tasks": 5},
    "openclaw": {"execute": True, "read_all": False, "write_memory": False, "delegate": False, "max_tasks": 2},
}


@mcp.tool()
async def add_finding(content: str, agent: str = "claude-code") -> str:
    """Record a finding/discovery to the shared findings log. Use when you discover something useful during a task."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{ts}] {agent}\n{content}\n"
    if not _FINDINGS.exists():
        _FINDINGS.write_text("# Findings - NexusHive\n\nHallazgos de los agentes.\n\n", encoding="utf-8")
    with open(_FINDINGS, "a", encoding="utf-8") as f:
        f.write(entry)
    return json.dumps({"recorded": True, "agent": agent, "file": str(_FINDINGS)})


@mcp.tool()
async def add_decision(decision: str, reason: str, agent: str = "claude-code") -> str:
    """Record a decision and its reasoning. Builds the system's learning history."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## [{ts}] {agent}\n**Decision:** {decision}\n**Reason:** {reason}\n"
    if not _DECISIONS.exists():
        _DECISIONS.write_text("# Decisions - NexusHive\n\nDecisiones y razonamiento.\n\n", encoding="utf-8")
    with open(_DECISIONS, "a", encoding="utf-8") as f:
        f.write(entry)
    return json.dumps({"recorded": True, "agent": agent, "file": str(_DECISIONS)})


@mcp.tool()
async def read_cloud() -> str:
    """Read the master instructions file (cloud.md). Contains system identity, rules, and BLAST framework config."""
    if not _CLOUD.exists():
        return json.dumps({"error": "cloud.md not initialized. Run nexus_autonomous_loop.py --cycles 1 to create it."})
    content = _CLOUD.read_text(encoding="utf-8")
    return json.dumps({"content": content}, ensure_ascii=False)


@mcp.tool()
async def check_permissions(agent: str) -> str:
    """Check what permissions an agent has in the Suprawall security system."""
    perms = _AGENT_PERMS.get(agent)
    if not perms:
        return json.dumps({"error": f"Unknown agent: {agent}", "known_agents": list(_AGENT_PERMS.keys())})
    return json.dumps({"agent": agent, "permissions": perms}, indent=2)


# ============================================================
# NEXUS MEMORY (observations + findings — nexus_memory.db)
# ============================================================
_MEMORY_DB = Path(NEXUS_HOME) / "proyectos" / "supernexus-v2" / "memory" / "nexus_memory.db"
if not _MEMORY_DB.exists():
    _MEMORY_DB = Path(__file__).resolve().parents[2] / "memory" / "nexus_memory.db"


def _get_memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_MEMORY_DB), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _init_memory_db():
    conn = _get_memory_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS observations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        content TEXT NOT NULL,
        category TEXT DEFAULT 'general',
        project TEXT DEFAULT 'supernexus-v2',
        metadata TEXT DEFAULT '{}'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        agent TEXT NOT NULL,
        content TEXT NOT NULL,
        topic TEXT DEFAULT ''
    )""")
    # FTS5 index for fast search
    try:
        c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts
            USING fts5(content, category, project, content='observations', content_rowid='id')""")
    except Exception:
        pass  # Already exists or FTS5 not available
    conn.commit()
    conn.close()

_init_memory_db()


@mcp.tool()
async def add_observation(
    content: str,
    category: str = "general",
    project: str = "supernexus-v2",
    agent: str = "claude-code",
    metadata: str = "{}",
) -> str:
    """Add an observation to nexus_memory.db. Use for reports, task results, analysis, and any persistent findings. Categories: general, report, task, analysis, ide_capabilities, deepseek-tui, vision, sprint."""
    conn = _get_memory_conn()
    c = conn.cursor()
    ts = datetime.now().isoformat()
    c.execute(
        "INSERT INTO observations (ts, content, category, project, metadata) VALUES (?, ?, ?, ?, ?)",
        (ts, content, category, project, json.dumps({"agent": agent, **(json.loads(metadata) if metadata != "{}" else {})})),
    )
    obs_id = c.lastrowid
    # Update FTS index
    try:
        c.execute("INSERT INTO observations_fts (rowid, content, category, project) VALUES (?, ?, ?, ?)",
                  (obs_id, content, category, project))
    except Exception:
        pass
    conn.commit()
    conn.close()
    return json.dumps({"id": obs_id, "timestamp": ts, "category": category, "agent": agent}, indent=2)


@mcp.tool()
async def search_observations(
    query: str = "",
    category: str = "",
    project: str = "",
    limit: int = 10,
) -> str:
    """Search observations in nexus_memory.db. Use query for FTS5 full-text search, or filter by category/project. This is the primary knowledge base for tasks, reports, and analysis."""
    conn = _get_memory_conn()
    c = conn.cursor()
    if query:
        # FTS5 search
        try:
            c.execute(
                "SELECT o.id, o.ts, o.content, o.category, o.project FROM observations o "
                "JOIN observations_fts f ON o.id = f.rowid "
                "WHERE observations_fts MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            )
        except Exception:
            # Fallback to LIKE
            c.execute(
                "SELECT id, ts, content, category, project FROM observations "
                "WHERE content LIKE ? ORDER BY id DESC LIMIT ?",
                (f"%{query}%", limit),
            )
    elif category:
        c.execute(
            "SELECT id, ts, content, category, project FROM observations "
            "WHERE category = ? ORDER BY id DESC LIMIT ?",
            (category, limit),
        )
    else:
        c.execute(
            "SELECT id, ts, content, category, project FROM observations "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    rows = c.fetchall()
    conn.close()
    results = [
        {"id": r[0], "timestamp": r[1], "content": r[2][:500], "category": r[3], "project": r[4]}
        for r in rows
    ]
    return json.dumps({"results": results, "count": len(results)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_observation(obs_id: int) -> str:
    """Get a single observation by ID from nexus_memory.db. Returns full content without truncation."""
    conn = _get_memory_conn()
    c = conn.cursor()
    c.execute("SELECT id, ts, content, category, project, metadata FROM observations WHERE id = ?", (obs_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return json.dumps({"error": f"Observation {obs_id} not found"})
    return json.dumps({
        "id": row[0], "timestamp": row[1], "content": row[2],
        "category": row[3], "project": row[4], "metadata": row[5],
    }, indent=2, ensure_ascii=False)


@mcp.tool()
async def add_task_finding(
    content: str,
    topic: str = "",
    agent: str = "claude-code",
) -> str:
    """Record a task finding in nexus_memory.db. Use for task progress, completions, and results that need to persist."""
    conn = _get_memory_conn()
    c = conn.cursor()
    ts = datetime.now().isoformat()
    c.execute(
        "INSERT INTO findings (timestamp, agent, content, topic) VALUES (?, ?, ?, ?)",
        (ts, agent, content, topic),
    )
    fid = c.lastrowid
    conn.commit()
    conn.close()
    return json.dumps({"id": fid, "timestamp": ts, "agent": agent, "topic": topic}, indent=2)


@mcp.tool()
async def list_findings(
    agent: str = "",
    topic: str = "",
    limit: int = 10,
) -> str:
    """List findings from nexus_memory.db. Filter by agent or topic."""
    conn = _get_memory_conn()
    c = conn.cursor()
    query = "SELECT id, timestamp, agent, content, topic FROM findings WHERE 1=1"
    params = []
    if agent:
        query += " AND agent = ?"
        params.append(agent)
    if topic:
        query += " AND topic LIKE ?"
        params.append(f"%{topic}%")
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    results = [
        {"id": r[0], "timestamp": r[1], "agent": r[2], "content": r[3][:500], "topic": r[4]}
        for r in rows
    ]
    return json.dumps({"results": results, "count": len(results)}, indent=2, ensure_ascii=False)


@mcp.tool()
async def memory_stats() -> str:
    """Get nexus_memory.db statistics — observations count, findings count, categories, agents."""
    conn = _get_memory_conn()
    c = conn.cursor()
    stats = {"db_path": str(_MEMORY_DB)}
    try:
        c.execute("SELECT COUNT(*) FROM observations")
        stats["total_observations"] = c.fetchone()[0]
        c.execute("SELECT DISTINCT category FROM observations")
        stats["categories"] = [r[0] for r in c.fetchall()]
        c.execute("SELECT COUNT(*) FROM findings")
        stats["total_findings"] = c.fetchone()[0]
        c.execute("SELECT DISTINCT agent FROM findings")
        stats["finding_agents"] = [r[0] for r in c.fetchall()]
    except Exception as e:
        stats["error"] = str(e)
    conn.close()
    return json.dumps(stats, indent=2, ensure_ascii=False)


# ============================================================
# New Modules: AdaptiveRouter, SelfLearning, HierarchicalMemory
# ============================================================


@mcp.tool()
async def router_stats() -> str:
    """Get AdaptiveRouter statistics — Thompson Sampling outcomes per model, success rates, alpha/beta distributions."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from src.core.adaptive_router import AdaptiveRouter
        router = AdaptiveRouter()
        stats = router.get_stats()
        return json.dumps({"router_stats": stats, "candidates": router.get_candidates("")}, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def router_select(task: str, prefer_speed: bool = False, prefer_quality: bool = False) -> str:
    """Select the best model for a task using Thompson Sampling. Returns model name and all candidates with scores."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from src.core.adaptive_router import AdaptiveRouter
        router = AdaptiveRouter()
        model = router.select_model(task, prefer_speed=prefer_speed, prefer_quality=prefer_quality)
        candidates = router.get_candidates(task)
        return json.dumps({"selected": model, "prefer_speed": prefer_speed, "prefer_quality": prefer_quality,
                           "candidates": candidates}, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def self_learning_status() -> str:
    """Get SelfLearningLoop status — cycles, pending records, last cycle timestamp."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from src.core.self_learning_loop import SelfLearningLoop
        loop = SelfLearningLoop()
        return json.dumps({"status": "SelfLearningLoop module loaded",
                           "actor": "self_learning_loop",
                           "description": "Continuous learning cycle that records outcomes and feeds AdaptiveRouter"}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def memory_hierarchical_stats() -> str:
    """Get HierarchicalMemory statistics — total items, tier distribution, capacities."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from src.core.hierarchical_memory import HierarchicalMemory
        mem = HierarchicalMemory()
        return json.dumps({"hierarchical_memory": mem.get_stats()}, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def memory_hierarchical_store(content: str, tags: str = "", importance: float = 0.5, tier: str = "working") -> str:
    """Store an item in HierarchicalMemory. Tiers: working, episodic, semantic. Tags comma-separated."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from src.core.hierarchical_memory import HierarchicalMemory
        mem = HierarchicalMemory()
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        item = mem.store(content, tags=tag_list, importance=importance, tier=tier)
        return json.dumps({"id": item.id, "tier": item.tier, "importance": item.importance, "tags": item.tags}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def memory_hierarchical_search(query: str, tier: str = "", min_importance: float = 0.0, top_k: int = 10) -> str:
    """Search HierarchicalMemory across 3 tiers. Returns items with scores."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from src.core.hierarchical_memory import HierarchicalMemory
        mem = HierarchicalMemory()
        tier_arg = tier if tier else None
        results = mem.search(query, tier=tier_arg, min_importance=min_importance, top_k=top_k)
        return json.dumps({
            "query": query,
            "results": [{"content": r.content[:200], "tier": r.tier, "score": round(r.decay_score, 3),
                         "tags": r.tags, "importance": r.importance}
                        for r in results],
            "count": len(results),
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


@mcp.tool()
async def retrieval_search(query: str, top_k: int = 10) -> str:
    """Multi-signal retrieval: hybrid search combining semantic + keyword + entity matching."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from src.core.multi_signal_retrieval import MultiSignalRetrieval
        retriever = MultiSignalRetrieval()
        entities = retriever.extract_entities(query)
        kw_score_fn = lambda text: retriever.keyword_search(text, query)  # noqa: E731
        return json.dumps({
            "query": query,
            "entities_found": entities,
            "signals": ["vector", "keyword", "entity"],
            "note": "Connect vector_search_fn and keyword_search_fn for full multi-signal results",
        }, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)


# ============================================================
# Entry point for MCP Clients (Claude Desktop, Gemini, etc.)
# ============================================================
if __name__ == "__main__":
    mcp.run()


