#!/usr/bin/env python3
"""
NEXUS Remote Console - Consola para controlar NEXUS en Remote Node desde PC1
"""

import asyncio
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Instalando httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

import os

Remote Node_URL = os.environ.get("SUPER_NEXUS_Remote Node_URL", "http://${REMOTE_NODE_IP}:9000")
PC1_URL = os.environ.get("SUPER_NEXUS_PC1_URL", "http://localhost:9000")

BANNER = """
+----------------------------------------------------------+
|  NEXUS Remote Console - Remote Node Control desde PC1            |
|  Escribe 'help' para ver comandos disponibles             |
|  Escribe 'exit' o 'quit' para salir                       |
+----------------------------------------------------------+
"""

HELP_TEXT = """
Comandos disponibles:
  chat <mensaje>          - Enviar mensaje al Director de Remote Node
  gem <nombre> <mensaje>  - Usar gema especifica (director, code, scholar, etc)
  status                  - Estado de Remote Node (CPU, RAM, GPU, servicios)
  models                  - Modelos Ollama en Remote Node
  exec <comando>          - Ejecutar comando SSH en Remote Node
  files <ruta>            - Listar archivos en Remote Node
  learn <texto>           - Ensenar algo a la memoria de Remote Node
  memory <query>          - Buscar en memoria de Remote Node
  ping                    - Verificar conexion con Remote Node
  local <mensaje>         - Enviar mensaje a NEXUS local (PC1)
  help                    - Mostrar esta ayuda
  exit / quit             - Salir
"""


class NexusRemoteConsole:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.current_gem = "auto"
        self.history = []

    async def ping(self):
        """Verificar conexión con Remote Node y PC1"""
        # Remote Node
        try:
            r = await self.client.get(f"{Remote Node_URL}/api/status", timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                print(f"\n[OK] Remote Node ONLINE - NEXUS v{data.get('version', '?')}")
                print(f"  Director: {data.get('director', {}).get('identity', {}).get('name', '?')}")
                print(f"  Gems: {data.get('director', {}).get('gemas_count', 0)}")
            else:
                # Remote Node puede no tener /api/status, probar con otro endpoint
                r = await self.client.get(f"{Remote Node_URL}/api/tools", timeout=5.0)
                if r.status_code == 200:
                    print(f"\n[OK] Remote Node ONLINE (API disponible)")
                else:
                    print(f"\n[?] Remote Node responde pero sin status estandar")
        except Exception as e:
            print(f"\n[ERROR] Remote Node OFFLINE: {e}")

        # PC1
        try:
            r = await self.client.get(f"{PC1_URL}/api/status", timeout=5.0)
            if r.status_code == 200:
                data = r.json()
                print(f"[OK] PC1 ONLINE - SuperNEXUS v{data.get('version', '?')}")
        except Exception as e:
            print(f"[ERROR] PC1 OFFLINE: {e}")

    async def chat(self, message, gem=None):
        """Enviar mensaje a Remote Node"""
        gem = gem or self.current_gem
        try:
            # Remote Node usa campo 'prompt', PC1 usa 'message'
            # Intentamos primero con Remote Node
            for url, label in [(Remote Node_URL, "Remote Node"), (PC1_URL, "PC1")]:
                try:
                    # Probar con campo 'prompt' (Remote Node)
                    r = await self.client.post(
                        f"{url}/api/chat",
                        json={"prompt": message, "gem": gem},
                        timeout=60.0,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        if "error" not in data or data.get("reply"):
                            reply = data.get("reply", data.get("response", ""))
                            gem_used = data.get("gem", data.get("gem_used", "?"))
                            model = data.get("model", "?")
                            duration = data.get("duration_ms", 0)
                            tokens = data.get("tokens_used", 0)

                            print(f"\n[{label}/{gem_used}] ({model}) - {duration:.0f}ms, {tokens} tokens")
                            print("-" * 60)
                            print(reply)
                            print("-" * 60)
                            return reply
                    # Probar con campo 'message' (PC1)
                    r = await self.client.post(
                        f"{url}/api/chat",
                        json={"message": message, "gem": gem},
                        timeout=60.0,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        reply = data.get("reply", data.get("response", ""))
                        gem_used = data.get("gem", data.get("gem_used", "?"))
                        model = data.get("model", "?")
                        duration = data.get("duration_ms", 0)
                        tokens = data.get("tokens_used", 0)

                        print(f"\n[{label}/{gem_used}] ({model}) - {duration:.0f}ms, {tokens} tokens")
                        print("-" * 60)
                        print(reply)
                        print("-" * 60)
                        return reply
                except Exception:
                    continue
            print(f"\n[ERROR] No se pudo conectar con Remote Node ni PC1")
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")

    async def Remote Node_status(self):
        """Estado detallado de Remote Node"""
        try:
            r = await self.client.get(f"{Remote Node_URL}/api/system/stats", timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                print(f"\n{'='*50}")
                print(f"  Remote Node SYSTEM STATUS")
                print(f"{'='*50}")
                for key, value in data.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in value.items():
                            print(f"    {k}: {v}")
                    else:
                        print(f"  {key}: {value}")
                print(f"{'='*50}")
        except Exception as e:
            print(f"\n[ERROR] Error obteniendo status: {e}")

    async def Remote Node_models(self):
        """Modelos Ollama en Remote Node"""
        try:
            r = await self.client.get(f"{Remote Node_URL}/api/ollama/models", timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                models = data.get("models", [])
                print(f"\n{'='*50}")
                print(f"  MODELOS OLLAMA EN Remote Node")
                print(f"{'='*50}")
                for m in models:
                    name = m.get("name", "?")
                    size = m.get("size", "?")
                    print(f"  • {name} ({size})")
                print(f"{'='*50}")
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")

    async def Remote Node_exec(self, command):
        """Ejecutar comando en Remote Node via SSH bridge"""
        try:
            r = await self.client.post(
                f"{Remote Node_URL}/api/mcp/Remote Node",
                json={"command": command},
                timeout=30.0,
            )
            if r.status_code == 200:
                data = r.json()
                output = data.get("output", "")
                success = data.get("success", False)
                print(f"\n{'='*50}")
                print(f"  Remote Node EXEC: {command}")
                print(f"{'='*50}")
                if output:
                    print(output)
                else:
                    print("(sin salida)")
                print(f"{'='*50}")
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")

    async def Remote Node_files(self, path):
        """Listar archivos en Remote Node"""
        await self.Remote Node_exec(f"ls -la {path}")

    async def learn(self, text):
        """Enseñar a la memoria de Remote Node"""
        try:
            r = await self.client.post(
                f"{Remote Node_URL}/api/learn",
                json={"query": text},
                timeout=30.0,
            )
            if r.status_code == 200:
                data = r.json()
                print(f"\n[OK] Aprendido: {data.get('success', False)}")
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")

    async def memory_search(self, query):
        """Buscar en memoria de Remote Node"""
        try:
            r = await self.client.post(
                f"{Remote Node_URL}/api/memory/search",
                json={"query": query},
                timeout=10.0,
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                count = data.get("count", 0)
                print(f"\n{'='*50}")
                print(f"  MEMORIA Remote Node: {count} resultados para '{query}'")
                print(f"{'='*50}")
                for i, r in enumerate(results, 1):
                    print(f"  {i}. {r}")
                print(f"{'='*50}")
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")

    async def local_chat(self, message):
        """Enviar mensaje a NEXUS local (PC1)"""
        try:
            r = await self.client.post(
                f"{PC1_URL}/api/chat",
                json={"message": message, "gem": "auto"},
                timeout=60.0,
            )
            if r.status_code == 200:
                data = r.json()
                reply = data.get("reply", "")
                gem_used = data.get("gem_used", "?")
                model = data.get("model", "?")
                duration = data.get("duration_ms", 0)
                print(f"\n[PC1/{gem_used}] ({model}) - {duration:.0f}ms")
                print("-" * 60)
                print(reply)
                print("-" * 60)
        except Exception as e:
            print(f"\n[ERROR] Error: {e}")

    async def process_command(self, line):
        """Procesar línea de comando"""
        line = line.strip()
        if not line:
            return

        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("exit", "quit", "q"):
            return "exit"
        elif cmd == "help" or cmd == "?":
            print(HELP_TEXT)
        elif cmd == "ping":
            await self.ping()
        elif cmd == "status":
            await self.Remote Node_status()
        elif cmd == "models":
            await self.Remote Node_models()
        elif cmd == "exec" and args:
            await self.Remote Node_exec(args)
        elif cmd == "files" and args:
            await self.Remote Node_files(args)
        elif cmd == "learn" and args:
            await self.learn(args)
        elif cmd == "memory" and args:
            await self.memory_search(args)
        elif cmd == "local" and args:
            await self.local_chat(args)
        elif cmd == "gem" and args:
            gem_parts = args.split(maxsplit=1)
            if len(gem_parts) == 2:
                self.current_gem = gem_parts[0]
                await self.chat(gem_parts[1], gem=gem_parts[0])
            else:
                print(f"Uso: gem <nombre> <mensaje>")
        elif cmd == "chat" and args:
            await self.chat(args)
        else:
            # Si no es comando, enviar como chat a Remote Node
            await self.chat(line)

    async def run(self):
        """Loop principal de la consola"""
        print(BANNER)
        await self.ping()

        while True:
            try:
                line = input(f"\n[Remote Node:{self.current_gem}]> ")
                result = await self.process_command(line)
                if result == "exit":
                    print("\nSaliendo...")
                    break
            except KeyboardInterrupt:
                print("\n\nSaliendo...")
                break
            except EOFError:
                print("\nSaliendo...")
                break
            except Exception as e:
                print(f"\n[ERROR] Error: {e}")

        await self.client.aclose()


def main():
    console = NexusRemoteConsole()
    asyncio.run(console.run())


if __name__ == "__main__":
    main()
