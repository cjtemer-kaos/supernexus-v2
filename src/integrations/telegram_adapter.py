"""
telegram_adapter — Minimal channel adapter for Telegram.

Pattern (openfang channels): long-polling bot that forwards every incoming
message to /api/chat with session_id=tg:{chat_id} so the budget tracker
+ runtime_logs see per-chat metrics. Reply goes back via sendMessage.

Activation:
    NEXUS_TELEGRAM_BOT_TOKEN     bot token from @BotFather (required)
    NEXUS_API_URL                where to POST chats (default localhost:9000)
    NEXUS_TELEGRAM_ALLOWED_CHATS optional whitelist (comma-sep chat IDs)

Usage:
    python -m src.integrations.telegram_adapter
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Optional, Set

logger = logging.getLogger("nexus.telegram")

TELEGRAM_API = "https://api.telegram.org"


def _allowed_chats() -> Optional[Set[int]]:
    raw = os.environ.get("NEXUS_TELEGRAM_ALLOWED_CHATS", "").strip()
    if not raw:
        return None
    out = set()
    for tok in raw.split(","):
        try:
            out.add(int(tok.strip()))
        except ValueError:
            pass
    return out or None


async def _send_message(client, token: str, chat_id: int, text: str):
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    try:
        await client.post(url, json={
            "chat_id": chat_id, "text": text[:4096],
            "parse_mode": "Markdown",
        })
    except Exception as e:
        logger.warning(f"sendMessage failed: {e}")


async def _post_chat(client, api_url: str, text: str, chat_id: int) -> str:
    """Forward text to /api/chat. Returns reply or error string."""
    try:
        r = await client.post(
            f"{api_url}/api/chat",
            json={"message": text, "session_id": f"tg:{chat_id}"},
            timeout=120.0,
        )
        if r.status_code >= 400:
            return f"⚠️ NEXUS HTTP {r.status_code}"
        data = r.json()
        return data.get("reply") or "(empty reply)"
    except Exception as e:
        return f"⚠️ NEXUS error: {type(e).__name__}: {e}"


async def run():
    token = os.environ.get("NEXUS_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: NEXUS_TELEGRAM_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    api_url = os.environ.get("NEXUS_API_URL", "http://localhost:9000").rstrip("/")
    allowed = _allowed_chats()
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx not installed (pip install httpx)", file=sys.stderr)
        sys.exit(1)

    print(f"[telegram] starting | api={api_url} | "
          f"allowed_chats={'all' if allowed is None else len(allowed)}")
    offset = 0
    async with httpx.AsyncClient(timeout=35.0) as client:
        while True:
            try:
                r = await client.get(
                    f"{TELEGRAM_API}/bot{token}/getUpdates",
                    params={"offset": offset, "timeout": 30},
                )
                data = r.json()
                if not data.get("ok"):
                    logger.warning(f"getUpdates not ok: {data}")
                    await asyncio.sleep(5)
                    continue
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    msg = upd.get("message")
                    if not msg or "text" not in msg:
                        continue
                    chat_id = msg["chat"]["id"]
                    text = msg["text"]
                    if allowed and chat_id not in allowed:
                        logger.info(f"ignored chat {chat_id} (not whitelisted)")
                        continue
                    print(f"[telegram] chat={chat_id} text={text[:80]!r}")
                    reply = await _post_chat(client, api_url, text, chat_id)
                    await _send_message(client, token, chat_id, reply)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"poll error: {e}")
                await asyncio.sleep(5)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n[telegram] bye")


if __name__ == "__main__":
    main()
