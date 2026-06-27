"""
colmena_hive.py — HIVE HUB integration para opencode y claude-code.

Dual-channel:
  - HIVE HUB WS + dispatch (para agentes que lo soportan: director, opencode)
  - message_board.db (para claude-code, que usa MCP tools hive_hub.send_message/read_messages)
"""
import asyncio
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

from src.core.db_wal import db_connection
from src.core.nexus_config import get_nexus_url

import aiohttp

HIVE_URL = os.environ.get("NEXUS_HIVE_URL") or get_nexus_url()
LOG_PATH = Path.home() / ".nexus" / "colmena_hive.log"
PID_FILE = Path.home() / ".nexus" / "colmena_hive.pid"
BOARD_PATH = Path.home() / ".nexus" / "brain" / "message_board.db"


def log_msg(msg):
    t = datetime.now().strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def send_to_board(target: str, content: str, sender: str = "opencode",
                  channel: str = "general", msg_type: str = "task"):
    """Write a message to message_board.db for claude-code to read via read_messages MCP tool."""
    try:
        conn = db_connection(str(BOARD_PATH), db_label="hive")
        c = conn.cursor()
        ts = datetime.now().isoformat()
        c.execute(
            "INSERT INTO messages (timestamp, sender, target, channel, content, msg_type) VALUES (?, ?, ?, ?, ?, ?)",
            (ts, sender, target, channel, content, msg_type),
        )
        msg_id = c.lastrowid
        conn.commit()
        conn.close()
        log_msg(f"Board #{msg_id} -> {target}: {content[:60]}")
        return msg_id
    except Exception as e:
        log_msg(f"Board write error: {e}")
        return None


def send_hive(task: str, agent: str = "claude", timeout: int = 30) -> dict:
    """Send task via HIVE HUB dispatch."""
    try:
        data = json.dumps({"agent": agent, "task": task}).encode()
        req = urllib.request.Request(
            f"{HIVE_URL}/api/hive/dispatch",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception as e:
        log_msg(f"Dispatch error: {e}")
        return {"ok": False, "error": str(e)}


def get_result(run_id: str) -> dict:
    """Get result from HIVE HUB."""
    try:
        resp = urllib.request.urlopen(f"{HIVE_URL}/api/hive/result/{run_id}", timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        return {"ok": False, "error": str(e)}


def post_hive_result(run_id: str, agent: str, task: str, reply: str):
    """Post result back to HIVE HUB."""
    try:
        post_data = json.dumps({
            "agent": agent, "task": task, "reply": reply, "ok": True
        }).encode()
        req = urllib.request.Request(
            f"{HIVE_URL}/api/hive/result/{run_id}",
            data=post_data,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        log_msg(f"Post result error: {e}")
        return False


async def process_with_ollama(task: str, model: str = "qwen2.5vl:7b",
                              system: str = "") -> str:
    """Process a task with Ollama and return the response."""
    try:
        prompt = system + "\n\n" + task if system else task
        data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:11834/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read())
        return result.get("response", "Procesado")
    except Exception as e:
        log_msg(f"Ollama error: {e}")
        return f"Error al procesar: {e}"


async def process_opencode_task(event: dict):
    """Process a task dispatched to opencode via HIVE HUB."""
    run_id = event.get("run_id", "")
    task = event.get("task", "")

    if not task:
        return

    log_msg(f"Processing opencode task: {task[:100]}")

    response = await process_with_ollama(
        task,
        system="Eres opencode, un agente del ecosistema SuperNEXUS v2. "
               "Responde de forma util y concisa en espanol."
    )

    post_hive_result(run_id, "opencode", task, response)

    send_to_board("claude-code",
                  f"[opencode responde a tarea #{run_id[:8]}]\n{response}",
                  msg_type="task_done")

    log_msg(f"Done: run_id={run_id}")


async def listen_ws():
    """Listen to HIVE HUB WebSocket for events."""
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(f"{HIVE_URL}/api/hive/ws") as ws:
            log_msg("Connected to HIVE HUB WS")
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    event = json.loads(msg.data)
                    event_type = event.get("type", "")

                    if event_type == "hive.hello":
                        log_msg(f"Connected: {len(event.get('agents', []))} agents")

                    elif event_type == "hive.dispatched":
                        agent = event.get("agent", "")
                        run_id = event.get("run_id", "")
                        task = event.get("task", "")[:100]
                        log_msg(f"Dispatched: {agent} <- {task} (run_id={run_id})")

                        if agent == "opencode":
                            asyncio.create_task(process_opencode_task(event))

                    elif event_type == "hive.finished":
                        agent = event.get("agent", "")
                        run_id = event.get("run_id", "")
                        ok = event.get("ok", False)
                        reply = event.get("reply", "")[:100]
                        log_msg(f"Finished: {agent} ok={ok} reply={reply}")

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    log_msg(f"WS error: {ws.exception()}")
                    break


def run():
    """Main entry point."""
    PID_FILE.write_text(str(os.getpid()))
    log_msg("Starting colmena_hive...")

    try:
        resp = urllib.request.urlopen(f"{HIVE_URL}/api/hive/agents", timeout=5)
        agents = json.loads(resp.read()).get("agents", [])
        log_msg(f"HIVE HUB connected: {len(agents)} agents")
    except Exception as e:
        log_msg(f"HIVE HUB not available: {e}")
        return

    try:
        asyncio.run(listen_ws())
    except KeyboardInterrupt:
        log_msg("Stopped")
    except Exception as e:
        log_msg(f"Error: {e}")
    finally:
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    run()
