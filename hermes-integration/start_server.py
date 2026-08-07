import os, sys
os.environ.pop('PYTHONPATH', None)
_hermes = os.path.expanduser('~/AppData/Local/hermes/hermes-agent')
sys.path = [p for p in sys.path if _hermes not in p and 'hermes-agent' not in p]
# Brain canonico: ~/.nexus/brain/ (donde todos los agentes escriben)
# No sobreescribir NEXUS_BRAIN — el default es ~/.nexus/brain
sys.path.insert(0, '.')
import asyncio

# Windows: use SelectorEventLoop. ProactorEventLoop drops timers/IO
# when many concurrent tasks (15+ workers) sleep simultaneously, freezing HTTP.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Auto-install bundled Ollama models on first boot (idempotent, non-fatal)
try:
    import subprocess
    subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "scripts", "install_models.py")],
        timeout=120, check=False,
    )
except Exception as _e:
    print(f"[startup] install_models skipped: {_e}")

# Ensure opencode zen config survives updates/overwrites
try:
    subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "scripts", "ensure_zen_config.py")],
        timeout=10, check=False,
    )
except Exception as _e:
    print(f"[startup] ensure_zen_config skipped: {_e}")

from src.api.server import run_server
port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
asyncio.run(run_server(port))
