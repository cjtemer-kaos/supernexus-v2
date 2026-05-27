"""
group_task.py - Comando central de tareas grupales
Uso: python group_task.py "descripcion de la tarea"
"""
import sqlite3
import sys
import os
import time
import subprocess
from datetime import datetime

DB = os.path.expanduser("~/.nexus/brain/message_board.db")
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_hidden(cmd):
    if sys.platform == 'win32':
        subprocess.Popen(cmd, creationflags=0x08000000,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    if len(sys.argv) < 2:
        print("Uso: python group_task.py 'descripcion de la tarea'")
        return

    task = sys.argv[1]
    agents = ["opencode", "claude-code", "antigravity", "openclaw"]

    print(f"=== TAREA GRUPAL ===")
    print(f"Task: {task}")
    print(f"Agentes: {', '.join(agents)}\n")

    conn = sqlite3.connect(DB)

    # 1. Enviar tareas
    for agent in agents:
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), 'supernexus', agent, 'tasks', task, 'task', '{}'))
        print(f"  -> Enviado a {agent}")

    conn.commit()

    # 2. Despertar agentes
    wake_script = os.path.join(PROJECT, "src", "control", "nexus-wake.py")
    run_hidden(["python", wake_script, "all"])
    print("\n  -> Agentes despertados")

    # 3. Esperar respuestas
    print("\nEsperando respuestas (30s)...")
    time.sleep(30)

    # 4. Recopilar respuestas
    print("\n=== RESULTADOS ===\n")
    for agent in agents:
        msgs = conn.execute(
            'SELECT content FROM messages WHERE sender=? AND msg_type="task_done" ORDER BY id DESC LIMIT 1',
            (agent,)
        ).fetchall()
        if msgs:
            print(f"  {agent}: {msgs[0][0][:150]}...")
        else:
            print(f"  {agent}: (procesando...)")

    conn.close()
    print("\n=== TAREA GRUPAL COMPLETADA ===")

if __name__ == "__main__":
    main()
