import discord
import httpx
import asyncio
import os
import logging
from dotenv import load_dotenv

# Configuración de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("discord-bot")

# Cargar variables de entorno
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
# SuperNEXUS v2.0 API corre por defecto en el puerto 9001 para el backend
API_URL = os.getenv("NEXUS_API_URL", "http://localhost:9001/api/chat")

class NexusDiscordClient(discord.Client):
    async def on_ready(self):
        logger.info(f'Bot conectado como {self.user} (ID: {self.user.id})')
        logger.info(f'Conectado a Nexus API: {API_URL}')
        logger.info('--- Ready to serve Nexus skills ---')

    async def on_message(self, message):
        # Debug: Mostrar TODO lo que entra
        logger.info(f"DEBUG_MSG: {message.author} en #{getattr(message.channel, 'name', 'N/A')} - Contenido: '{message.content}'")
        
        # Ignorar mensajes del propio bot
        if message.author == self.user:
            return

        # Responder si el bot es mencionado, es canal DM, o es en el canal asistente-ia
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user.mentioned_in(message)
        is_channel = getattr(message.channel, "name", "") == "asistente-ia"
        
        if is_mention or is_dm or is_channel:
            async with message.channel.typing():
                # Limpiar mención del contenido
                clean_content = message.content.replace(f'<@!{self.user.id}>', '').replace(f'<@{self.user.id}>', '').strip()
                
                logger.info(f"Mensaje recibido: {clean_content}")
                
                try:
                    async with httpx.AsyncClient() as client:
                        # Enviar a SuperNEXUS v2 API
                        response = await client.post(API_URL, json={
                            "message": clean_content,
                            "project": "default",
                            "gem": "auto"
                        }, timeout=300.0)
                        
                        if response.status_code == 200:
                            data = response.json()
                            reply = data.get("reply", "No hubo respuesta de NEXUS.")
                            
                            # Limitar longitud para Discord (2000 chars)
                            if len(reply) > 1900:
                                reply = reply[:1897] + "..."
                                
                            await message.reply(reply)
                        else:
                            await message.reply(f"❌ Error de conexión con NEXUS (Status: {response.status_code})\nVerifica que el servidor API (`python -m src.api.server`) esté corriendo.")
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
                    await message.reply(f"⚠️ Hubo un error al procesar tu solicitud: {str(e)}")

def main():
    if not TOKEN:
        logger.error("No se encontró DISCORD_TOKEN en el entorno.")
        print("="*60)
        print("ERROR: DISCORD_TOKEN no configurado.")
        print("Por favor, agrega DISCORD_TOKEN=tu_token a un archivo .env en la raíz de supernexus-v2")
        print("="*60)
        return

    intents = discord.Intents.default()
    intents.message_content = True
    
    client = NexusDiscordClient(intents=intents)
    client.run(TOKEN)

if __name__ == "__main__":
    main()
