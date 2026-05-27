"""
NexusHive Autonomous Loop para JARVIS Mark XXXIX
Escucha tareas del Message Board SQLite y las resuelve
enviando comandos a la API HTTP de JARVIS (puerto 9039).
"""
import sqlite3, os, sys, time, json, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

JARVIS_API = "http://localhost:9039"
DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
AGENT_NAME = "jarvis-code"
CHECK_INTERVAL = 5


class JarvisAutonomousLoop:
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
            "SELECT metadata FROM messages WHERE sender=? AND msg_type='task_done' ORDER BY id DESC LIMIT 1",
            (self.agent_name,)).fetchone()
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
        print("[JARVIS-LOOP] last_id: %d" % self.last_id)

    def check_tasks(self):
        conn = sqlite3.connect(DB_PATH)
        tasks = conn.execute(
            "SELECT id, sender, target, content, msg_type FROM messages "
            "WHERE target IN (?, '*') AND msg_type='task' AND id > ? ORDER BY id ASC",
            (self.agent_name, self.last_id)).fetchall()
        conn.close()
        if tasks:
            self.last_id = tasks[-1][0]
        return [{"id": t[0], "sender": t[1], "target": t[2], "content": t[3], "type": t[4]} for t in tasks]

    def _call_jarvis(self, prompt):
        """Envía prompt a JARVIS API y devuelve la respuesta."""
        data = json.dumps({"text": prompt, "speak": False}).encode("utf-8")
        req = urllib.request.Request(
            "%s/command" % JARVIS_API,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def process_task(self, task):
        content = task["content"]
        sender = task["sender"]
        task_id = task["id"]
        print("[%s] Task #%d from %s" % (datetime.now().strftime("%H:%M:%S"), task_id, sender))
        result = self._call_jarvis(content)
        reply = result.get("response") or result.get("reply") or json.dumps(result)
        self._send_response(sender, reply, task_id)
        print("[JARVIS-LOOP] Response sent for task #%d" % task_id)

    def _send_response(self, target, content, task_id):
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), self.agent_name, target, "general",
             "[JARVIS] " + str(content)[:2000], "task_done", json.dumps({"task_id": task_id})))
        conn.commit()
        conn.close()

    def run(self):
        print("=== JARVIS autonomous loop started ===")
        print("Listening on target: %s" % self.agent_name)
        while True:
            try:
                tasks = self.check_tasks()
                for task in tasks:
                    self.process_task(task)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print("[JARVIS-LOOP] Error: %s" % str(e))
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    JarvisAutonomousLoop().run()
