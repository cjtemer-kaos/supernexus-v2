"""
NexusHive Autonomous Loop para Agent Zero
Escucha tareas del Message Board SQLite y las resuelve
ejecutando la API programática oficial de Agent Zero.
"""
import sqlite3
import os
import sys
import time
import json
import asyncio
import types
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Asegurar que Agent Zero corra en modo local sin delegación por RFC/Development
if "--dockerized" not in "".join(sys.argv):
    sys.argv.append("--dockerized=true")

# Evitar problemas de encoding en la consola de Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
ZERO_PATH = os.environ.get("AGENT_ZERO_PATH", str(Path(PROJECT_ROOT) / "external" / "agent-zero"))

# Agregar rutas al sys.path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if ZERO_PATH not in sys.path:
    sys.path.insert(0, ZERO_PATH)

# Cargar variables .env de SuperNexus
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Mapear clave para el proveedor compatible con OpenAI que LiteLLM requiere
if "ANTHROPIC_API_KEY" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]
    os.environ["CUSTOM_OPENAI_API_KEY"] = os.environ["ANTHROPIC_API_KEY"]

# Registrar dinámicamente el modelo gratuito en LiteLLM
try:
    import litellm
    litellm.register_model({
        "custom_openai/qwen3.6-plus-free": {
            "max_tokens": 4096,
            "litellm_provider": "custom_openai"
        },
        "custom_openai/deepseek-v4-flash-free": {
            "max_tokens": 4096,
            "litellm_provider": "custom_openai"
        },
        "custom_openai/minimax-m2.5-free": {
            "max_tokens": 4096,
            "litellm_provider": "custom_openai"
        },
        "custom_openai/nemotron-3-super-free": {
            "max_tokens": 4096,
            "litellm_provider": "custom_openai"
        }
    })
    print("[ZERO-LOOP] Modelos personalizados registrados en LiteLLM.")
except Exception as e:
    print(f"[ZERO-LOOP] Error al registrar modelos en LiteLLM: {e}")

# Crear un mock de whisper para evitar errores de importación de audio
mock_whisper = types.ModuleType("whisper")
mock_whisper.load_model = lambda *args, **kwargs: None
sys.modules["whisper"] = mock_whisper

# Ahora podemos importar de forma segura los módulos de Agent Zero
try:
    from agent import AgentContext, UserMessage, AgentContextType
    from initialize import initialize_agent
    print("[ZERO-LOOP] Módulos de Agent Zero importados correctamente.")
except Exception as e:
    print(f"[ZERO-LOOP] Error crítico al importar Agent Zero: {e}")

DB_PATH = os.path.expanduser("~/.nexus/brain/message_board.db")
AGENT_NAME = "zero-code"
CHECK_INTERVAL = 10

class ZeroAutonomousLoop:
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
        print(f"[ZERO-LOOP] last_id inicializado al último completado o actual MAX(id) - 1: {self.last_id}")

    def check_tasks(self):
        conn = sqlite3.connect(DB_PATH)
        tasks = conn.execute('''SELECT id, sender, target, content, msg_type FROM messages
            WHERE target IN (?, '*') AND msg_type = 'task' AND id > ?
            ORDER BY id ASC''', (self.agent_name, self.last_id)).fetchall()
        conn.close()

        if tasks:
            self.last_id = tasks[-1][0]
        return [{"id": t[0], "sender": t[1], "target": t[2], "content": t[3], "type": t[4]} for t in tasks]

    async def execute_zero_agent(self, prompt):
        """Invoca a Agent Zero programáticamente y retorna su respuesta final"""
        print(f"[ZERO-LOOP] Iniciando razonamiento de Agent Zero para el prompt...")
        try:
            # Forzar el modo local nativo (bypass de RFC/Development)
            from helpers import runtime
            runtime.initialize()
            runtime.args["dockerized"] = "true"
            
            # Inicializar la configuración del agente (lee de usr/settings.json y .env)
            config = initialize_agent()
            
            # Crear un contexto de usuario
            context = AgentContext(config=config, type=AgentContextType.USER)
            AgentContext.use(context.id)
            
            # Iniciar la comunicación de forma asíncrona
            task = context.communicate(UserMessage(message=prompt))
            result = await task.result()
            
            # Liberar el contexto
            AgentContext.remove(context.id)
            
            return str(result)
        except Exception as e:
            return f"[ERROR AGENT ZERO] Ocurrió una excepción durante la ejecución: {str(e)}"

    async def process_task(self, task):
        content = task["content"]
        sender = task["sender"]
        task_id = task["id"]

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Procesando tarea #{task_id} de {sender}")
        response = await self.execute_zero_agent(content)
        
        self._send_response(sender, response, task_id)
        print(f"[ZERO-LOOP] Respuesta enviada con éxito.")

    def _send_response(self, target, content, task_id):
        conn = sqlite3.connect(DB_PATH)
        conn.execute('''INSERT INTO messages (timestamp, sender, target, channel, content, msg_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), self.agent_name, target, 'general',
             f"[REAL-ZERO] {content}", 'task_done', json.dumps({"task_id": task_id})))
        conn.commit()
        conn.close()

    async def run(self):
        print(f"=== Agent Zero autonomous loop iniciado ===")
        print(f"Escuchando target: {self.agent_name}")
        while True:
            try:
                tasks = self.check_tasks()
                for task in tasks:
                    await self.process_task(task)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ZERO-LOOP] Error en loop: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    loop = ZeroAutonomousLoop()
    asyncio.run(loop.run())
