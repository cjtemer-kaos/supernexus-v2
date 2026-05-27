"""
Discord Bot v3 - Interfaz completa para DirectorNexus de PC2

PC2 es una maquina independiente con:
- 22 gemas especializadas (code, debugger, scholar, etc.)
- Herramientas: terminal, archivos, git, grep, glob
- Agent Loop TDAO (Think-Decide-Act-Observe)
- Skills: 1,449+ skills disponibles
- GPU AMD + 11 modelos Ollama

El bot expone TODAS estas capacidades via Discord.
"""

import discord
import asyncio
import os
import sys
import logging
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Agregar project root al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configuracion de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "discord_bridge.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger("discord-bot-pc2")

load_dotenv(PROJECT_ROOT / ".env")

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_NAME = os.getenv("DISCORD_CHANNEL", "asistente-ia")

# System prompt global de DirectorNexus - se inyecta en cada mensaje
DIRECTOR_IDENTITY = """Eres DirectorNexus, el cerebro central de SuperNEXUS v2.0, un ecosistema autonomo de IA local.

IDENTIDAD:
- Nombre: DirectorNexus v2.0
- Rol: Cerebro orquestador de SuperNEXUS
- Arquitectura: Brain + Tools (tu eres el cerebro, los modelos son herramientas)
- Ubicacion: PC2 (Linux con GPU AMD, red local)

CAPACIDADES:
- 22 gemas especializadas: code, debugger, scholar, architect, creative, sage, analyst, engineer, optimizer, tester, security, devops, trainer, biblioteca, vision, opencode, codex, design, music, prompter, producer, director
- Herramientas: terminal, archivos, git, grep, glob, busqueda web
- Skills: 1,449+ skills disponibles bajo demanda
- Modelos: Ollama local (qwen2.5-coder, deepseek-r1, nemotron, gemma, etc.)
- GPU: AMD Radeon con ROCm

REGLAS:
- Responde en español de forma directa y util
- NO digas que eres una IA generica o asistente virtual
- NO inventes personalidades o nombres que no sean DirectorNexus
- Cuando te pregunten quien eres, di que eres DirectorNexus v2.0 corriendo en PC2
- Ofrece usar tus herramientas cuando sea relevante
- Si puedes ejecutar algo directamente, hazlo en lugar de solo explicarlo
"""

# Estado global
director = None
director_lock = asyncio.Lock()


async def get_director():
    """Obtener instancia del DirectorNexus local de PC2 (singleton lazy)"""
    global director
    if director is None:
        async with director_lock:
            if director is None:
                logger.info("Inicializando DirectorNexus de PC2...")
                try:
                    from src.core.director import DirectorNexus
                    director = DirectorNexus(project="default")
                    asyncio.create_task(director.initialize_self_model())
                    # Iniciar background workers
                    asyncio.create_task(director.start_background_workers())
                    logger.info("DirectorNexus de PC2 inicializado")
                    logger.info(f"  - 22 gemas disponibles")
                    logger.info(f"  - {len(director.ai_tools.tools)} AI tools")
                    logger.info(f"  - {len(director.execution_log)} ejecuciones previas")
                except Exception as e:
                    logger.error(f"Error inicializando DirectorNexus: {e}")
                    raise
    return director


def format_response(text: str, max_chunk: int = 1900) -> list[str]:
    """Dividir respuesta en chunks para Discord"""
    if not text:
        return ["(sin respuesta)"]
    
    # Respetar bloques de codigo
    chunks = []
    while text:
        if len(text) <= max_chunk:
            chunks.append(text)
            break
        
        # Intentar cortar en un bloque de codigo
        cutoff = text.rfind("```", 0, max_chunk)
        if cutoff == -1:
            # Cortar en newline
            cutoff = text.rfind("\n", 0, max_chunk)
            if cutoff == -1:
                cutoff = max_chunk
        
        chunk = text[:cutoff]
        # Si cortamos dentro de un bloque de codigo, cerrarlo
        if chunk.count("```") % 2 == 1:
            chunk += "\n```"
        
        chunks.append(chunk)
        text = text[cutoff:].lstrip()
    
    return chunks


class NexusPC2DiscordClient(discord.Client):
    """Bot de Discord conectado al DirectorNexus local de PC2"""

    async def on_ready(self):
        logger.info(f'Bot PC2 conectado como {self.user} (ID: {self.user.id})')
        logger.info('Conectado al DirectorNexus LOCAL de PC2')
        logger.info(f'Canal activo: #{CHANNEL_NAME} + DMs + menciones')
        logger.info('--- PC2 Nexus Discord Bridge Ready ---')
        
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="SuperNEXUS v2 PC2"
        )
        await self.change_presence(activity=activity)

    def _should_respond(self, message) -> bool:
        """Verificar si debe responder a este mensaje"""
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user.mentioned_in(message)
        is_channel = getattr(message.channel, "name", "") == CHANNEL_NAME
        return is_mention or is_dm or is_channel

    async def _handle_command(self, message, cmd: str, args: str) -> bool:
        """
        Procesar comandos especiales.
        Retorna True si se proceso un comando.
        """
        d = await get_director()
        
        if cmd == "status":
            """Mostrar estado completo de PC2"""
            status = d.get_status()
            sm_status = status.get("self_model", {})
            
            embed = discord.Embed(
                title="PC2 - DirectorNexus Status",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Gemas", value=f"{status.get('gemas_count', 0)} disponibles", inline=True)
            embed.add_field(name="Ejecuciones", value=f"{status.get('executions', 0)}", inline=True)
            embed.add_field(name="Sesiones", value=f"{status.get('sessions', {}).get('total_sessions', 0)}", inline=True)
            
            if sm_status:
                embed.add_field(name="Self-Model", value=f"Capabilidades: {sm_status.get('capability_map_available', False)}", inline=True)
                embed.add_field(name="Routing Rules", value=f"{sm_status.get('routing_rules', 0)} aprendidas", inline=True)
                embed.add_field(name="Knowledge Boundaries", value=f"{sm_status.get('knowledge_boundaries', 0)}", inline=True)
            
            # Gemas con mejor rendimiento
            gemas = status.get("gemas", {})
            top_gemas = sorted(
                [(name, info) for name, info in gemas.items() if info.get("execution_count", 0) > 0],
                key=lambda x: x[1].get("success_rate", 0),
                reverse=True
            )[:5]
            
            if top_gemas:
                gemas_text = "\n".join(
                    f"{name}: {info['success_rate']:.0%} ({info['execution_count']})"
                    for name, info in top_gemas
                )
                embed.add_field(name="Top Gemas", value=f"```{gemas_text}```", inline=False)
            
            await message.reply(embed=embed)
            return True
        
        elif cmd == "tools":
            """Mostrar herramientas disponibles"""
            tools = d.ai_tools.get_available_tools()
            tools_text = "\n".join(
                f"**{t['name']}**: {', '.join(t['tags'][:3])}"
                for t in tools[:15]
            )
            
            embed = discord.Embed(
                title="PC2 - AI Tools",
                description=tools_text,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"{len(tools)} tools disponibles")
            await message.reply(embed=embed)
            return True
        
        elif cmd == "gema":
            """Ejecutar con una gema especifica: /gema code Escribe una funcion"""
            if not args:
                await message.reply("Uso: `/gema <nombre> <tarea>`\nEjemplo: `/gema code Escribe un script Python`")
                return True
            
            parts = args.split(" ", 1)
            if len(parts) < 2:
                await message.reply("Falta la tarea. Uso: `/gema <nombre> <tarea>`")
                return True
            
            gem_name, task = parts
            
            gemas_validas = list(d.gemas.keys())
            if gem_name not in gemas_validas:
                await message.reply(f"Gema no valida. Disponibles: {', '.join(gemas_validas)}")
                return True
            
            async with message.channel.typing():
                result = await d.execute(task=task, gem=gem_name)
                
                if result.success:
                    reply = result.data.get("content", "Completado sin output.")
                else:
                    reply = f"Error: {result.data.get('error', 'Error desconocido')}"
                
                for chunk in format_response(reply):
                    await message.reply(chunk)
            return True
        
        elif cmd == "run":
            """Ejecutar comando en terminal de PC2"""
            if not args:
                await message.reply("Uso: `/run <comando>`\nEjemplo: `/run ls -la`")
                return True
            
            async with message.channel.typing():
                try:
                    proc = await asyncio.create_subprocess_shell(
                        args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=str(PROJECT_ROOT),
                    )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                    
                    output = stdout.decode("utf-8", errors="replace")
                    error = stderr.decode("utf-8", errors="replace")
                    
                    reply = f"```bash\n$ {args}\n```"
                    if output:
                        reply += f"```\n{output[:1500]}\n```"
                    if error:
                        reply += f"**stderr:**\n```\n{error[:500]}\n```"
                    
                    for chunk in format_response(reply):
                        await message.reply(chunk)
                except asyncio.TimeoutError:
                    await message.reply("Timeout: el comando tardo mas de 60 segundos")
                except Exception as e:
                    await message.reply(f"Error ejecutando: {e}")
            return True
        
        elif cmd == "help":
            """Mostrar ayuda"""
            embed = discord.Embed(
                title="PC2 - Comandos Disponibles",
                color=discord.Color.gold(),
                description="PC2 es una maquina independiente con DirectorNexus, 22 gemas, GPU AMD y 11 modelos Ollama."
            )
            embed.add_field(
                name="Comandos",
                value=(
                    "`/status` - Estado del DirectorNexus\n"
                    "`/tools` - Herramientas AI disponibles\n"
                    "`/gema <nombre> <tarea>` - Ejecutar con gema especifica\n"
                    "`/run <comando>` - Ejecutar en terminal de PC2\n"
                    "`/help` - Esta ayuda\n"
                    "`<mensaje>` - Chat normal con el Director"
                ),
                inline=False
            )
            embed.add_field(
                name="Gemas Disponibles",
                value=(
                    "`code`, `debugger`, `scholar`, `architect`, `creative`,\n"
                    "`sage`, `analyst`, `engineer`, `optimizer`, `tester`,\n"
                    "`security`, `devops`, `trainer`, `biblioteca`, `vision`,\n"
                    "`opencode`, `codex`, `design`, `music`, `prompter`, `producer`"
                ),
                inline=False
            )
            await message.reply(embed=embed)
            return True
        
        return False

    async def on_message(self, message):
        if message.author == self.user:
            return

        if not self._should_respond(message):
            return

        async with message.channel.typing():
            clean_content = message.content.replace(f'<@!{self.user.id}>', '').replace(f'<@{self.user.id}>', '').strip()
            
            if not clean_content:
                return

            logger.info(f"Mensaje de {message.author}: {clean_content[:100]}...")

            # Verificar si es un comando
            if clean_content.startswith("/"):
                parts = clean_content[1:].split(" ", 1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                if await self._handle_command(message, cmd, args):
                    return
            
            # Chat normal con DirectorNexus - ejecutar en thread pool para evitar deadlock
            try:
                d = await get_director()
                
                # Inyectar identidad de DirectorNexus directamente en el task
                task_with_identity = f"""[SYSTEM: Eres DirectorNexus v2.0, el cerebro central de SuperNEXUS. Responde en español. NO inventes personalidades. Tu nombre es DirectorNexus.]

{clean_content}"""
                
                # Ejecutar en un thread separado para evitar conflictos de lock
                loop = asyncio.get_event_loop()
                
                async def execute_task():
                    classification = await d.classify_task(clean_content)
                    result = await d.execute(
                        task=task_with_identity,
                        gem="auto",
                        context=f"Discord user: {message.author.name}, channel: {message.channel}"
                    )
                    return classification, result
                
                classification, result = await execute_task()
                
                # Construir respuesta
                if result.success:
                    content = result.data.get("content", "")
                    gem_used = result.data.get("tool_used", "")
                    model_used = result.data.get("model_used", "")
                    
                    reply = content if content else "(Procesado, sin respuesta de contenido)"
                    
                    if len(reply) < 200 and (gem_used or model_used):
                        reply += f"\n\n---\n*Gema: `{gem_used}` | Modelo: `{model_used}`*"
                else:
                    error = result.data.get("error", "Error desconocido")
                    reply = f"Error: {error}"
                
                for chunk in format_response(reply):
                    await message.reply(chunk)
                    
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}", exc_info=True)
                await message.reply(f"Error al procesar: {str(e)[:200]}")


def main():
    if not TOKEN:
        logger.error("No se encontro DISCORD_TOKEN en el entorno.")
        print("=" * 60)
        print("ERROR: DISCORD_TOKEN no configurado.")
        print("Agrega DISCORD_TOKEN=tu_token al archivo .env")
        print("=" * 60)
        return

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    intents = discord.Intents.default()
    intents.message_content = True

    client = NexusPC2DiscordClient(intents=intents)

    try:
        logger.info("Iniciando bot de Discord para PC2...")
        client.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)


if __name__ == "__main__":
    main()
