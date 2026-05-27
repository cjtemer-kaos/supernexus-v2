"""
NexusHive Autonomous Loop para Qwen Code
Escucha tareas del Message Board SQLite y las resuelve de forma gratuita e ilimitada
ejecutando la CLI oficial de Qwen conectada al proxy local FreeQwenApi.
"""
import sqlite3
import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, PROJECT_ROOT)

DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
AGENT_NAME = "qwen-code"
CHECK_INTERVAL = 10

# Cargar variables .env
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class QwenAutonomousLoop:
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
        # Buscar el último mensaje completado por este agente
        row = conn.execute("SELECT metadata FROM messages WHERE sender = ? AND msg_type = 'task_done' ORDER BY id DESC LIMIT 1", (self.agent_name,)).fetchone()
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
                last_completed_id = max_row[0]
                
        self.last_id = last_completed_id
        print(f"last_id inicializado al último completado o actual MAX(id): {self.last_id}")


    def check_tasks(self):
        conn = sqlite3.connect(DB_PATH)
        tasks = conn.execute('''SELECT id, sender, target, content, msg_type FROM messages
            WHERE target IN (?, '*') AND msg_type = 'task' AND id > ?
            ORDER BY id ASC''', (self.agent_name, self.last_id)).fetchall()
        conn.close()

        if tasks:
            self.last_id = tasks[-1][0]
        return [{"id": t[0], "sender": t[1], "target": t[2], "content": t[3], "type": t[4]} for t in tasks]

    def execute_qwen_cli(self, prompt):
        """Invoca la CLI real de Qwen en subproceso conectada al proxy FreeQwenApi"""
        api_key = os.getenv("QWEN_API_KEY", "free-qwen-key")
        base_url = os.getenv("QWEN_BASE_URL", "http://localhost:3264/api")
        auth_type = os.getenv("QWEN_AUTH_TYPE", "openai")
        model = os.getenv("QWEN_MODEL", "qwen3-coder-plus")

        # Configurar entorno de subproceso
        env = os.environ.copy()
        env["OPENAI_API_KEY"] = api_key
        env["OPENAI_BASE_URL"] = base_url

        # Armar el comando CLI con modo YOLO
        cmd = [
            "qwen",
            prompt,
            "-y",  # YOLO: Auto-aprobación
            "--auth-type", auth_type,
            "--model", model,
            "--output-format", "text"
        ]

        print(f"  -> Ejecutando CLI Qwen: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                env=env,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=180,
                shell=True
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                return f"[ERROR QWEN CLI] {result.stderr or result.stdout}"
        except Exception as e:
            return f"[EXCEPCIÓN EJECUCIÓN] {str(e)}"

    def process_task(self, task):
        content = task["content"]
        sender = task["sender"]
        task_id = task["id"]

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Procesando tarea #{task_id} de {sender}")
        response = self.execute_qwen_cli(content)
        
        self._send_response(sender, response, task_id)
        print(f"  -> Respuesta enviada")

    def _send_response(self, target, content, task_id):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), self.agent_name, target, 'general',
             f"[REAL-QWEN-FREE] {content}", 'task_done', json.dumps({"task_id": task_id})))
        conn.commit()
        conn.close()

    def run(self):
        print(f"=== Qwen autonomous loop iniciado ===")
        print(f"Escuchando target: {self.agent_name}")
        while True:
            try:
                tasks = self.check_tasks()
                for task in tasks:
                    self.process_task(task)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error en loop: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    loop = QwenAutonomousLoop()
    loop.run()
