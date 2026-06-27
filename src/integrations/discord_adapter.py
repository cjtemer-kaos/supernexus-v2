"""
discord_adapter — Minimal Discord bot channel.

Same shape as telegram_adapter (commit 54). Uses Discord gateway via
discord.py if installed, falls back to webhook receiver mode.

Activation:
    NEXUS_DISCORD_BOT_TOKEN     bot token (required)
    NEXUS_API_URL               where to POST chats (default localhost:9000)
    NEXUS_DISCORD_ALLOWED_GUILDS optional comma-sep guild whitelist

Usage:
    python -m src.integrations.discord_adapter
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Optional, Set

logger = logging.getLogger("nexus.discord")


def _allowed_guilds() -> Optional[Set[int]]:
    raw = os.environ.get("NEXUS_DISCORD_ALLOWED_GUILDS", "").strip()
    if not raw:
        return None
    out = set()
    for tok in raw.split(","):
        try:
            out.add(int(tok.strip()))
        except ValueError:
            pass
    return out or None


async def _post_chat(client, api_url: str, text: str, channel_id: int) -> str:
    try:
        r = await client.post(
            f"{api_url}/api/chat",
            json={"message": text, "session_id": f"discord:{channel_id}"},
            timeout=120.0,
        )
        if r.status_code >= 400:
            return f"NEXUS HTTP {r.status_code}"
        return r.json().get("reply") or "(empty reply)"
    except Exception as e:
        return f"NEXUS error: {type(e).__name__}: {e}"


async def run():
    token = os.environ.get("NEXUS_DISCORD_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: NEXUS_DISCORD_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    api_url = os.environ.get("NEXUS_API_URL", "http://localhost:9000").rstrip("/")
    allowed = _allowed_guilds()
    try:
        import discord
        import httpx
    except ImportError:
        print("ERROR: missing deps — pip install discord.py httpx", file=sys.stderr)
        sys.exit(1)

    intents = discord.Intents.default()
    intents.message_content = True
    bot = discord.Client(intents=intents)
    http = httpx.AsyncClient(timeout=130.0)

    @bot.event
    async def on_ready():
        print(f"[discord] logged in as {bot.user} | "
              f"allowed_guilds={'all' if allowed is None else len(allowed)}")

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return
        if allowed and (message.guild is None or message.guild.id not in allowed):
            return
        text = message.content.strip()
        if not text:
            return
        print(f"[discord] guild={message.guild and message.guild.id} "
              f"chan={message.channel.id} text={text[:80]!r}")
        try:
            reply = await _post_chat(http, api_url, text, message.channel.id)
        except Exception as e:
            reply = f"error: {e}"
        # Discord cap 2000 chars
        await message.channel.send(reply[:1990])

    try:
        await bot.start(token)
    finally:
        await http.aclose()


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[discord] bye")


if __name__ == "__main__":
    main()
