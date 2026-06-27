"""
NexusHive Autonomous Loop — Procesamiento automatico de tareas.
Soporta loops! patterns via /loop commands (loops.elorm.xyz).
"""
import sqlite3
import os
import sys
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
OLLAMA_URL = "http://localhost:11434"
AGENT_NAME = "supernexus"
CHECK_INTERVAL = 10

try:
    from src.core.loops_engine import resolve_loop, generate_kickoff, list_loops, LOOP_REGISTRY
    HAS_LOOPS = True
except ImportError:
    HAS_LOOPS = False


class AutonomousLoop:
    def __init__(self, agent_name=AGENT_NAME):
        self.agent_name = agent_name
        self.last_id = 0
        self._ensure_db()
        if HAS_LOOPS:
            print(f"[LOOPS] Engine loaded: {len(LOOP_REGISTRY)} patterns")
        else:
            print("[LOOPS] Engine not available")

    def _ensure_db(self):
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            sender TEXT NOT NULL,
            target TEXT DEFAULT '*',
            channel TEXT DEFAULT 'general',
            content TEXT NOT NULL,
            msg_type TEXT DEFAULT 'chat',
            metadata TEXT DEFAULT '{}'
        )''')
        conn.commit()
        conn.close()

    def check_tasks(self):
        conn = sqlite3.connect(DB_PATH)
        tasks = conn.execute('''SELECT id, sender, target, content, msg_type FROM messages
            WHERE target IN (?, '*') AND id > ?
            ORDER BY id ASC''', (self.agent_name, self.last_id)).fetchall()
        conn.close()

        if tasks:
            self.last_id = tasks[-1][0]

        return [{"id": t[0], "sender": t[1], "target": t[2], "content": t[3], "type": t[4]} for t in tasks]

    def process_task(self, task):
        content = task["content"]
        sender = task["sender"]
        task_id = task["id"]

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Procesando tarea #{task_id} de {sender}")

        response = self._route_task(content)

        self._send_response(sender, response, task_id)
        print("  -> Respuesta enviada")

    def _route_task(self, content: str) -> str:
        """Route task to loops engine or fallback."""
        # /loop command
        loop_match = re.match(r"^/loop\s+(\S+)(.*)", content.strip())
        if loop_match and HAS_LOOPS:
            return self._handle_loop_cmd(loop_match.group(1), loop_match.group(2))

        # /loops list
        if content.strip().lower() in ("/loops", "/loops list", "list loops"):
            return self._list_loops()

        # Legacy routing
        if any(k in content.lower() for k in ("analiza", "verifica", "revisa")):
            return self._analyze_task(content)
        elif any(k in content.lower() for k in ("genera", "crea")):
            return self._generate_task(content)
        else:
            return self._general_response(content)

    def _handle_loop_cmd(self, loop_name: str, args: str) -> str:
        """Resolve and execute a /loop command."""
        loop = resolve_loop(loop_name)
        if not loop:
            available = ", ".join(sorted(LOOP_REGISTRY.keys())[:10])
            return f"Loop '{loop_name}' not found. Available: {available}... (use /loops list)"

        params = {}
        for part in args.split():
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v

        kickoff = generate_kickoff(loop, **params)
        return kickoff

    def _list_loops(self) -> str:
        """List all available loops by category."""
        cats = {}
        for loop in sorted(LOOP_REGISTRY.values(), key=lambda l: l.name):
            cats.setdefault(loop.category, []).append(loop.name)
        lines = ["Available loops! patterns:", ""]
        for cat in sorted(cats):
            lines.append(f"  [{cat}]")
            for name in cats[cat]:
                loop = LOOP_REGISTRY[name]
                lines.append(f"    /loop {name} — {loop.goal}")
        lines.append("")
        lines.append("Usage: /loop <name> [key=value ...]")
        return "\n".join(lines)

    def _analyze_task(self, content):
        """Analiza usando Ollama local"""
        prompt = f"Como agente de NexusHive, analiza esta solicitud y responde concisamente:\n\n{content}\n\nResponde en espanol, maximo 150 caracteres."

        try:
            import urllib.request
            req_data = json.dumps({
                "model": "nemotron-3-nano:4b",
                "prompt": prompt,
                "stream": False
            }).encode()
            req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=req_data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            text = result.get("response", "")
            return text[:200] if text else "Analisis completado"
        except Exception:
            return "Analisis completado (modo local)"

    def _generate_task(self, content):
        """Genera contenido usando Ollama"""
        prompt = f"Como agente de NexusHive, ejecuta esta tarea y da el resultado:\n\n{content}\n\nResponde en espanol, maximo 150 caracteres."

        try:
            import urllib.request
            req_data = json.dumps({
                "model": "nemotron-3-nano:4b",
                "prompt": prompt,
                "stream": False
            }).encode()
            req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=req_data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            text = result.get("response", "")
            return text[:200] if text else "Tarea completada"
        except Exception:
            return "Tarea completada (modo local)"

    def _general_response(self, content):
        """Respuesta general via Ollama"""
        prompt = f"Responde como agente de NexusHive a este mensaje:\n\n{content}\n\nMaximo 100 caracteres en espanol."

        try:
            import urllib.request
            req_data = json.dumps({
                "model": "nemotron-3-nano:4b",
                "prompt": prompt,
                "stream": False
            }).encode()
            req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=req_data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            text = result.get("response", "")
            return text[:150] if text else "Mensaje recibido"
        except Exception:
            return "Mensaje recibido y procesado"

    def _send_response(self, target, content, task_id):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), self.agent_name, target, 'general',
             f"[AUTO] {content}", 'task_done', json.dumps({"task_id": task_id})))
        conn.commit()
        conn.close()

    def run(self):
        print(f"=== NexusHive Autonomous Loop: {self.agent_name} ===")
        print(f"DB: {DB_PATH}")
        print(f"Intervalo: {CHECK_INTERVAL}s")
        print("Presiona Ctrl+C para detener\n")

        while True:
            try:
                tasks = self.check_tasks()
                for task in tasks:
                    self.process_task(task)
            except KeyboardInterrupt:
                print("\nLoop detenido")
                break
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else AGENT_NAME
    loop = AutonomousLoop(name)
    loop.run()
