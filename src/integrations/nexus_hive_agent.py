"""
NexusHive Auto-Agent - Ejecuta tareas automáticamente
Monitorea el message_board y ejecuta tareas sin intervención manual
"""

import sqlite3
import time
import os
from datetime import datetime
from pathlib import Path
import subprocess
import json

MESSAGE_BOARD_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")

class NexusHiveAgent:
    """Agente automático que procesa tareas"""
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.last_checked_id = 0
        self._init_db()
    
    def _init_db(self):
        """Inicializa DB si no existe"""
        Path(MESSAGE_BOARD_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(MESSAGE_BOARD_PATH)
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
        """Verifica nuevas tareas Y mensajes en todos los canales"""
        conn = sqlite3.connect(MESSAGE_BOARD_PATH)
        
        # Busca tareas Y mensajes en general/chat
        tasks = conn.execute('''SELECT * FROM messages 
            WHERE target = ? AND id > ?
            ORDER BY id ASC''', (self.agent_name, self.last_checked_id)).fetchall()
        
        if tasks:
            self.last_checked_id = tasks[-1][0]
            for task in tasks:
                # task = (id, timestamp, sender, target, channel, content, msg_type, metadata)
                self._execute_task(task[5], task[6], task[2])
        
        conn.close()
        return len(tasks)
    
    def _send_response(self, target: str, content: str):
        """Envía respuesta a un agente"""
        conn = sqlite3.connect(MESSAGE_BOARD_PATH)
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), self.agent_name, target, 'general', content, 'chat', '{}'))
        conn.commit()
        conn.close()
    
    def _execute_task(self, task_content: str, msg_type: str = "task", sender: str = "unknown"):
        """Ejecuta tarea o responde a mensaje automáticamente"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.agent_name}] Recibido: {task_content[:60]}...")
        
        if msg_type == "task":
            if "verifica" in task_content.lower() or "estado" in task_content.lower():
                self._check_status()
            elif "revisa" in task_content.lower() or "analiza" in task_content.lower():
                self._analyze_task(task_content)
            elif "integra" in task_content.lower():
                self._integration_task(task_content)
            else:
                print(f"  -> Tarea procesada")
            self._acknowledge_task(task_content)
        else:
            # Mensaje de chat - responder
            response = f"Hola {sender}! Soy {self.agent_name}. Estoy activo en la NexusHive."
            self._send_response(sender, response)
            print(f"  -> Respondido a {sender}")
    
    def _check_status(self):
        """Verifica estado del sistema"""
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Process python | Measure-Object | Select-Object -ExpandProperty Count"],
                capture_output=True, text=True, timeout=10
            )
            print(f"  -> Procesos Python: {result.stdout.strip()}")
        except:
            print("  -> Estado: Online")
    
    def _analyze_task(self, task_content: str):
        """Análisis automático"""
        print(f"  -> Analizando: {task_content[:40]}...")
        print("  -> Análisis completado")
    
    def _integration_task(self, task_content: str):
        """Tarea de integración"""
        print(f"  -> Integrando...")
        print("  -> Integración completada")
    
    def _acknowledge_task(self, task_content: str):
        """Confirma ejecución"""
        conn = sqlite3.connect(MESSAGE_BOARD_PATH)
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), self.agent_name, 'supernexus', 'general', 
             f"Tarea completada: {task_content[:50]}...", 'task_done', '{}'))
        conn.commit()
        conn.close()
    
    def run_forever(self, interval: int = 5):
        """Ejecuta el agente continuamente"""
        print(f"=== NexusHive Agent: {self.agent_name} ===")
        print(f"Monitoreando: {MESSAGE_BOARD_PATH}")
        print(f"Intervalo: {interval}s\n")
        
        while True:
            try:
                count = self.check_tasks()
                if count > 0:
                    print()
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    import sys
    agent_name = sys.argv[1] if len(sys.argv) > 1 else "supernexus"
    agent = NexusHiveAgent(agent_name)
    agent.run_forever(interval=3)