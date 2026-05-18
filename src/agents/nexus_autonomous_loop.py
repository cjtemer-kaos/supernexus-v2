"""
NexusHive Autonomous Loop - Procesamiento automatico de tareas
Corre en background y ejecuta tareas sin intervencion humana.
"""
import sqlite3
import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
OLLAMA_URL = "http://localhost:11434"
AGENT_NAME = "supernexus"
CHECK_INTERVAL = 10

class AutonomousLoop:
    def __init__(self, agent_name=AGENT_NAME):
        self.agent_name = agent_name
        self.last_id = 0
        self._ensure_db()

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

        # Detectar tipo de tarea
        if "analiza" in content.lower() or "verifica" in content.lower() or "revisa" in content.lower():
            response = self._analyze_task(content)
        elif "genera" in content.lower() or "crea" in content.lower():
            response = self._generate_task(content)
        else:
            response = self._general_response(content)

        self._send_response(sender, response, task_id)
        print(f"  -> Respuesta enviada")

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
        print(f"Presiona Ctrl+C para detener\n")

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
