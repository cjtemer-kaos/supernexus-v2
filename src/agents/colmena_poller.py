"""
colmena_poller.py — Autonomous loop + notifier para la colmena.
- opencode: procesa y responde automaticamente via Ollama
- claude-code: notifica via toast (no tenemos su CLI)
Corre en background sin ventana.
Uso: python colmena_poller.py [agent1,agent2,...]
     Por defecto: opencode,claude-code
"""
import sqlite3
import os
import time
import json
import sys
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
LOG_PATH = Path(os.path.expanduser("~/.nexus/colmena_poller.log"))
PID_FILE = Path(os.path.expanduser("~/.nexus/colmena_poller.pid"))
CHECK_INTERVAL = 10
OLLAMA_URL = "http://127.0.0.1:11834"
OPENCLAW_URL = "http://127.0.0.1:18789"

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    line = f"[{t}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def _toast(title, body):
    try:
        req = urllib.request.Request(
            f"{OPENCLAW_URL}/api/notify",
            data=json.dumps({"title": title, "body": body}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
        return
    except Exception:
        pass
    try:
        subprocess.run([
            "powershell", "-NoProfile",
            f'[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]::CreateToastNotifier("NEXUS Colmena").Show((New-Object Windows.UI.Notifications.ToastNotification("<toast><visual><binding template=\'ToastText02\'><text id=\'1\'>{title}</text><text id=\'2\'>{body}</text></binding></visual></toast>")))'
        ], capture_output=True, timeout=5)
    except Exception:
        pass

class ColmenaAutoLoop:
    def __init__(self, agents=None):
        self.agents = agents or ["opencode", "claude-code"]
        self.last_id = 0
        self._init_last_id()

    def _init_last_id(self):
        if not os.path.exists(DB_PATH):
            log("DB not found yet, will retry")
            return
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT MAX(id) FROM messages").fetchone()
        conn.close()
        self.last_id = row[0] - 1 if row and row[0] else 0
        log(f"Watching {self.agents} from msg_id={self.last_id}")

    def _get_new(self):
        if not os.path.exists(DB_PATH):
            return []
        placeholders = ",".join("?" for _ in self.agents)
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            f"SELECT id, sender, target, content, msg_type FROM messages WHERE (target IN ({placeholders}) OR target = '*') AND id > ? ORDER BY id ASC",
            (*self.agents, self.last_id)
        ).fetchall()
        conn.close()
        if rows:
            self.last_id = rows[-1][0]
        return rows

    def _ollama(self, prompt, model="qwen2.5vl:7b", max_tokens=500):
        try:
            data = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": max_tokens}}).encode()
            req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=data, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            return result.get("response", "").strip()
        except Exception as e:
            log(f"Ollama error: {e}")
            return None

    def _auto_respond(self, recipient, content, task_id, agent_name):
        log(f"#{task_id} GENERATING response for {recipient}...")
        prompt = f"Eres opencode, un agente del ecosistema SuperNEXUS v2. Recibiste este mensaje de {recipient} dirigido a {agent_name}:\n\n{content}\n\nResponde de forma util y concisa en espanol."
        response = self._ollama(prompt)
        if response:
            conn = sqlite3.connect(DB_PATH)
            conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (datetime.now().isoformat(), "opencode", recipient, "general",
                 response, "task_done", json.dumps({"task_id": task_id, "auto": True, "for": agent_name})))
            conn.commit()
            conn.close()
            log(f"#{task_id} RESPONDED to {recipient} ({len(response)} chars)")
        else:
            _toast(f"⚠️ Ollama down — mensaje de {recipient}", content[:120])
            log(f"#{task_id} CANNOT respond (ollama down)")

    def process(self, msg):
        tid, sender, target, content, mtype = msg
        preview = content[:150] if content else "(empty)"

        # Skip own messages to avoid loops
        if sender == "opencode" or sender == "auto-test" or sender == "test-poller":
            log(f"#{tid} SKIP (self): {sender} -> {target}")
            return

        if target == "claude-code" or target == "*":
            _toast(f"📬 {sender} -> claude-code", preview)
            log(f"#{tid} NOTIFY {sender} -> claude-code: {preview}")
            # Try to auto-process claude-code tasks too
            if mtype == "task" and target == "claude-code":
                self._auto_respond(sender, content, tid, "claude-code")
            return

        if target == "opencode":
            log(f"#{tid} PROCESS {sender} -> opencode: {preview}")
            self._auto_respond(sender, content, tid, "opencode")

    def run(self):
        PID_FILE.write_text(str(os.getpid()))
        log(f"Started PID={os.getpid()}, watching {self.agents}")
        while True:
            try:
                for msg in self._get_new():
                    self.process(msg)
            except KeyboardInterrupt:
                break
            except Exception as e:
                log(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)
        PID_FILE.unlink(missing_ok=True)
        log("Stopped")

if __name__ == "__main__":
    agents = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    ColmenaAutoLoop(agents).run()
