"""
NexusHive Autonomous Loop para OpenClaw
Escucha tareas del Message Board SQLite y las resuelve
ejecutando la CLI de OpenClaw (openclaw agent -m).
"""
import sqlite3
import os
import sys
import time
import json
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
load_dotenv(os.path.join(PROJECT_ROOT, ".env"), encoding="utf-8-sig")

DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
AGENT_NAME = "openclaw"
CHECK_INTERVAL = 10
OPENCLAW_CMD = os.environ.get("OPENCLAW_CMD", "openclaw")
GATEWAY_PORT = 18789


def is_gateway_running():
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{GATEWAY_PORT}/health")
        urllib.request.urlopen(req, timeout=3)
        return True
    except Exception:
        return False


def start_gateway():
    if is_gateway_running():
        return True
    print("[OPENCLAW-LOOP] Starting gateway...")
    try:
        subprocess.Popen(
            [OPENCLAW_CMD, "gateway", "start", "--auth", "none"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        for _ in range(10):
            time.sleep(1)
            if is_gateway_running():
                print("[OPENCLAW-LOOP] Gateway started.")
                return True
        print("[OPENCLAW-LOOP] Gateway failed to start.")
        return False
    except Exception as e:
        print(f"[OPENCLAW-LOOP] Gateway start error: {e}")
        return False


class OpenClawAutonomousLoop:
    def __init__(self):
        self.agent_name = AGENT_NAME
        self.last_id = 0
        self._ensure_db()
        self._init_last_id()

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

    def _init_last_id(self):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT metadata FROM messages WHERE sender = ? AND msg_type = 'task_done' ORDER BY id DESC LIMIT 1",
            (self.agent_name,)
        ).fetchone()
        conn.close()

        last_completed_id = 0
        if row and row[0]:
            try:
                meta = json.loads(row[0])
                last_completed_id = meta.get("task_id", 0)
            except Exception:
                pass

        if last_completed_id == 0:
            conn = sqlite3.connect(DB_PATH)
            max_row = conn.execute("SELECT MAX(id) FROM messages").fetchone()
            conn.close()
            if max_row and max_row[0]:
                last_completed_id = max_row[0] - 1

        self.last_id = last_completed_id
        print(f"[OPENCLAW-LOOP] last_id={self.last_id}")

    def check_tasks(self):
        conn = sqlite3.connect(DB_PATH)
        tasks = conn.execute('''SELECT id, sender, target, content, msg_type FROM messages
            WHERE target IN (?, '*') AND msg_type = 'task' AND id > ?
            ORDER BY id ASC''', (self.agent_name, self.last_id)).fetchall()
        conn.close()

        if tasks:
            self.last_id = tasks[-1][0]
        return [{"id": t[0], "sender": t[1], "target": t[2], "content": t[3], "type": t[4]} for t in tasks]

    def execute_openclaw(self, prompt):
        """Ejecuta openclaw infer model run (one-shot, JSON, local)"""
        cmd = [OPENCLAW_CMD, "infer", "model", "run",
               "--model", "ollama/qwen2.5-coder:7b",
               "--prompt", prompt, "--local", "--json"]
        print("[OPENCLAW-LOOP] Executing: openclaw infer model run ...")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8",
                errors="ignore", timeout=120, shell=True
            )
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if data.get("ok"):
                        texts = [o.get("text", "") for o in data.get("outputs", []) if o.get("text")]
                        return "\n".join(texts) if texts else str(data)
                    return str(data)
                except json.JSONDecodeError:
                    return result.stdout.strip() or result.stderr.strip()
            else:
                return f"[ERROR OPENCLAW] exit={result.returncode}: {result.stderr[:300]}"
        except subprocess.TimeoutExpired:
            return "[ERROR OPENCLAW] Timeout after 120s"
        except Exception as e:
            return f"[ERROR OPENCLAW] {str(e)}"

    def process_task(self, task):
        content = task["content"]
        sender = task["sender"]
        task_id = task["id"]

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Task #{task_id} from {sender}")
        response = self.execute_openclaw(content)

        self._send_response(sender, response, task_id)
        print("[OPENCLAW-LOOP] Response sent.")

    def _send_response(self, target, content, task_id):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), self.agent_name, target, 'general',
             f"[REAL-OPENCLAW] {content}", 'task_done', json.dumps({"task_id": task_id})))
        conn.commit()
        conn.close()

    def run(self):
        print("=== OpenClaw autonomous loop iniciado ===")
        start_gateway()
        print(f"Escuchando target: {self.agent_name}")
        while True:
            try:
                tasks = self.check_tasks()
                for task in tasks:
                    self.process_task(task)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[OPENCLAW-LOOP] Error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    loop = OpenClawAutonomousLoop()
    loop.run()
