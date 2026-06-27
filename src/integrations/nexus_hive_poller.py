import sqlite3
import time
import os
import sys
from pathlib import Path

# Fix stdout Cp1252 print crash
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BRAIN_DIR = Path(os.path.expanduser("~/.nexus/brain"))
DB_PATH = BRAIN_DIR / "message_board.db"

def watch_hive(agent_name: str = "antigravity"):
    print(f"=== Monitoreando Message Board para {agent_name} ===")
    print(f"DB Path: {DB_PATH}\n")
    
    last_id = 0
    # Inicialmente obtener último ID para solo mostrar mensajes nuevos
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT MAX(id) FROM messages").fetchone()
        last_id = row[0] if row[0] is not None else 0
        conn.close()

    try:
        while True:
            if DB_PATH.exists():
                conn = sqlite3.connect(DB_PATH)
                rows = conn.execute("SELECT id, timestamp, sender, content, msg_type FROM messages WHERE id > ? ORDER BY id ASC", (last_id,)).fetchall()
                for row in rows:
                    msg_id, ts, sender, content, msg_type = row
                    print(f"[{ts}] {sender} ({msg_type}): {content}")
                    last_id = msg_id
                conn.close()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nMonitoreo finalizado.")

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "antigravity"
    watch_hive(name)
