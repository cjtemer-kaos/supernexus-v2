#!/usr/bin/env python3
"""
Discord Bot for Hermes Agent - Chat interface
Sends messages to Hermes via webhook.
"""
import discord
from discord.ext import commands
import os, sys, json, hashlib, hmac, time

# Load config from .env
config = {}
env_path = os.path.join(os.path.dirname(__file__), '.env')
with open(env_path) as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            config[k] = v

DISCORD_TOKEN = config.get('DISCORD_TOKEN')
# Direct connection to Hermes Gateway API (no webhook)
HERMES_GATEWAY_URL = config.get('HERMES_GATEWAY_URL', 'http://127.0.0.1:8642/api/chat')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user} (ID: {bot.user.id})')
    print(f'Guilds: {len(bot.guilds)}')
    for guild in bot.guilds:
        print(f'  - {guild.name} ({guild.id})')

@bot.event
async def on_message(message):
    # Ignore own messages
    if message.author == bot.user:
        return
    
    # Process commands
    await bot.process_commands(message)
    
    # If message mentions bot, starts with 'ia', or is DM, respond
    content = message.content
    is_mention = bot.user.mentioned_in(message)
    starts_with_ia = content.lower().startswith('ia ')
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    if is_mention or starts_with_ia or is_dm:
        # Remove mention or 'ia' prefix from message
        for mention in [f'<@{bot.user.id}>', f'<@!{bot.user.id}>']:
            content = content.replace(mention, '').strip()
        if content.lower().startswith('ia '):
            content = content[3:].strip()
        
        if not content:
            await message.channel.send("¿En qué puedo ayudarte?")
            return
        
        # Send typing indicator
        async with message.channel.typing():
            # Direct request to Hermes Gateway API
            import urllib.request
            try:
                data = json.dumps({"message": content}).encode()
                req = urllib.request.Request(
                    HERMES_GATEWAY_URL,
                    data=data,
                    headers={
                        "Content-Type": "application/json"
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    response = json.loads(r.read())
                    reply = response.get("reply", "No reply from Hermes")
            except Exception as e:
                reply = f"Error connecting to Hermes: {e}"
        
        # Send response
        await message.channel.send(reply)

@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f'Pong! Latency: {round(bot.latency * 1000)}ms')

@bot.command(name='status')
async def status(ctx):
    await ctx.send(f'Bot: {bot.user}\nGuilds: {len(bot.guilds)}\nLatency: {round(bot.latency * 1000)}ms')

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env")
        sys.exit(1)
    
    print("Starting Discord bot for Hermes...")
    bot.run(DISCORD_TOKEN)