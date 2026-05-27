"""
NexusHive Autonomous Loop para Aider
Escucha tareas del Message Board SQLite y las resuelve
ejecutando Aider CLI en modo de consulta no interactiva.
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

# Evitar problemas de encoding en la consola de Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, PROJECT_ROOT)

DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
AGENT_NAME = "aider-code"
CHECK_INTERVAL = 10

# Cargar variables .env
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class AiderAutonomousLoop:
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
                # Restamos 1 para asegurar que procese la tarea que acaba de ingresar y que causó que nos despertaran
                last_completed_id = max_row[0] - 1
                
        self.last_id = last_completed_id
        print(f"[AIDER-LOOP] last_id inicializado al último completado o actual MAX(id) - 1: {self.last_id}")

    def check_tasks(self):
        conn = sqlite3.connect(DB_PATH)
        tasks = conn.execute('''SELECT id, sender, target, content, msg_type FROM messages
            WHERE target IN (?, '*') AND msg_type = 'task' AND id > ?
            ORDER BY id ASC''', (self.agent_name, self.last_id)).fetchall()
        conn.close()

        if tasks:
            self.last_id = tasks[-1][0]
        return [{"id": t[0], "sender": t[1], "target": t[2], "content": t[3], "type": t[4]} for t in tasks]

    def execute_aider_cli(self, prompt):
        """Invoca la CLI de Aider en subproceso en modo no interactivo"""
        env = os.environ.copy()
        
        # Intentar ejecutar con python -m aider o con aider directamente
        cmd = [
            "python", "-m", "aider.main",
            "--message", prompt,
            "--no-auto-commits",
            "--yes"  # Responder "sí" a las preguntas confirmatorias
        ]

        print(f"  -> Ejecutando CLI Aider: {' '.join(cmd)}")
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
                # Si falló, intentar fallback a la palabra clave "aider"
                fallback_cmd = [
                    "aider",
                    "--message", prompt,
                    "--no-auto-commits",
                    "--yes"
                ]
                print(f"  -> Reintentando con comando global: {' '.join(fallback_cmd)}")
                fallback_result = subprocess.run(
                    fallback_cmd,
                    env=env,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    timeout=180,
                    shell=True
                )
                if fallback_result.returncode == 0:
                    return fallback_result.stdout
                else:
                    return f"[ERROR AIDER CLI] Fallaron ambos intentos. Detalle: {fallback_result.stderr or fallback_result.stdout}"
        except Exception as e:
            return f"[EXCEPCIÓN EJECUCIÓN AIDER] {str(e)}"

    def process_task(self, task):
        content = task["content"]
        sender = task["sender"]
        task_id = task["id"]

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Procesando tarea #{task_id} de {sender}")
        response = self.execute_aider_cli(content)
        
        self._send_response(sender, response, task_id)
        print(f"  -> Respuesta enviada")

    def _send_response(self, target, content, task_id):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), self.agent_name, target, 'general',
             f"[REAL-AIDER] {content}", 'task_done', json.dumps({"task_id": task_id})))
        conn.commit()
        conn.close()

    def run(self):
        print(f"=== Aider autonomous loop iniciado ===")
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
    loop = AiderAutonomousLoop()
    loop.run()
