"""
nexus-wake.py - Despierta agentes de la colmena
Uso: python nexus-wake.py [agente]
Ejecuta en background sin consola visible.
"""
import sqlite3
import sys
import os
import subprocess
from datetime import datetime

DB = os.path.expanduser("~/.nexus/brain/message_board.db")
AGENT = sys.argv[1] if len(sys.argv) > 1 else "all"

def run_hidden(cmd):
    """Ejecuta comando sin ventana visible"""
    if sys.platform == 'win32':
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW, 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print(f"=== NexusHive Wake Call: {AGENT} ===", flush=True)
print(f"Hora: {datetime.now().strftime('%H:%M:%S')}", flush=True)

conn = sqlite3.connect(DB)

if AGENT == "all":
    targets = ["opencode", "claude-code", "antigravity", "openclaw"]
else:
    targets = [AGENT]

for t in targets:
    count = conn.execute(
        'SELECT COUNT(*) FROM messages WHERE target IN (?, "*") AND msg_type="task"',
        (t,)
    ).fetchone()[0]
    
    if count > 0:
        print(f"\n{t}: {count} tareas pendientes", flush=True)
        tasks = conn.execute(
            'SELECT id, sender, content FROM messages WHERE target IN (?, "*") AND msg_type="task" ORDER BY id DESC LIMIT 3',
            (t,)
        ).fetchall()
        for task in tasks:
            print(f"  #{task[0]} de {task[1]}: {task[2][:80]}...", flush=True)
        
        print(f"  -> Activando loop para {t}", flush=True)
        script = os.path.join(os.path.dirname(__file__), "..", "agents", "nexus_autonomous_loop.py")
        run_hidden(["python", script, t])
    else:
        print(f"\n{t}: Sin tareas", flush=True)

print(f"\nDB: {os.path.getsize(DB)} bytes", flush=True)
conn.close()
