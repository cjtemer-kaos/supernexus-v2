# hive_mind.py - RESTAURADO DESDE PC2
# Gestión de memoria distribuida y tareas soberanas

import sqlite3
import os
from datetime import datetime

class HiveMind:
    def __init__(self):
        nexus_home = os.getenv("NEXUS_HOME", os.path.expanduser("~/.nexus"))
        self.db_path = os.path.join(nexus_home, "memory", "hive_mind.db")

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.initialize_database()

    def initialize_database(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time DATETIME,
                end_time DATETIME
            )
        ''')
        self.conn.commit()

    def add_task(self, task_name):
        self.cursor.execute('''
            INSERT INTO tasks (task_name, status, start_time)
            VALUES (?, ?, ?)
        ''', (task_name, 'pending', datetime.now()))
        self.conn.commit()
        print(f"Task '{task_name}' registrada en Hive Mind.")

    def update_task_status(self, task_id, new_status):
        self.cursor.execute('''
            UPDATE tasks
            SET status = ?, end_time = ?
            WHERE id = ?
        ''', (new_status, datetime.now(), task_id))
        self.conn.commit()

    def list_all_tasks(self):
        self.cursor.execute('SELECT * FROM tasks ORDER BY id DESC LIMIT 10')
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()
