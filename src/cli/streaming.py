"""WebSocket streaming client for NEXUS chat."""
from __future__ import annotations

import asyncio
import json
import time

try:
    import websockets
    import websockets.client
    HAS_WS = True
except ImportError:
    HAS_WS = False

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text


async def stream_chat(
    host: str,
    token: str | None,
    message: str,
    console: Console,
    gem: str = "",
) -> str | None:
    """Stream chat response via WebSocket. Returns full response text."""
    if not HAS_WS:
        console.print("[red]websockets not installed. pip install websockets[/]")
        return None

    ws_url = host.replace("http://", "ws://").replace("https://", "wss://")
    url = f"{ws_url}/api/ws/chat"
    if token:
        url += f"?token={token}"

    payload = json.dumps({"message": message, "gem": gem})
    full_response = ""
    token_count = 0
    t0 = time.time()

    try:
        async with websockets.client.connect(url, close_timeout=3, ping_interval=10, ping_timeout=20, open_timeout=5) as ws:
            await ws.send(payload)

            # Show spinner until first token
            spinner_text = Text("⟳ Thinking...", style="bold cyan")
            first_token = True

            with Live(spinner_text, console=console, refresh_per_second=12, transient=True) as live:
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    # Handle different message types
                    msg_type = data.get("type", "")

                    if msg_type == "token" or "token" in data:
                        tok = data.get("token", data.get("content", ""))
                        if tok:
                            full_response += tok
                            token_count += 1
                            if first_token:
                                first_token = False
                            live.update(Markdown(full_response))

                    elif msg_type == "response" or "response" in data:
                        resp = data.get("response", data.get("content", ""))
                        if resp:
                            full_response = resp
                            live.update(Markdown(full_response))

                    elif msg_type == "error":
                        err = data.get("error", "Unknown error")
                        console.print(f"[red]✗ {err}[/]")
                        return None

                    elif msg_type in ("done", "end", "complete"):
                        break

    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "403" in err_str:
            console.print("[red]✗ Authentication failed. Use /login[/]")
        elif "refused" in err_str.lower() or "connect" in err_str.lower():
            console.print("[red]✗ Cannot connect to NEXUS API. Is the server running?[/]")
        else:
            console.print(f"[red]✗ Stream error: {err_str}[/]")
        return None

    elapsed = time.time() - t0

    # Print final formatted response if Live didn't render it fully
    if full_response:
        console.print()  # newline after Live
        console.print(Markdown(full_response))

    # Stats line
    if token_count > 0 and elapsed > 0:
        tps = token_count / elapsed
        console.print(
            f"[dim]─ {token_count} tokens │ {elapsed:.1f}s │ {tps:.0f} tok/s[/]"
        )
    elif elapsed > 0:
        console.print(f"[dim]─ {elapsed:.1f}s[/]")

    return full_response


def stream_chat_sync(
    host: str,
    token: str | None,
    message: str,
    console: Console,
    gem: str = "",
) -> str | None:
    """Synchronous wrapper for stream_chat."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context, create new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    stream_chat(host, token, message, console, gem),
                )
                return future.result(timeout=120)
        else:
            return loop.run_until_complete(
                stream_chat(host, token, message, console, gem)
            )
    except RuntimeError:
        return asyncio.run(stream_chat(host, token, message, console, gem))
