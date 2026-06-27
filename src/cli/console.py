"""NEXUS Console — Professional TUI REPL for SuperNEXUS v2.

Usage:
    python -m src.cli.console                  # Interactive REPL
    python -m src.cli.console --host URL       # Custom API host
    python -m src.cli.console --theme jarvis   # Theme selection
    echo "/status" | python -m src.cli.console # Pipe mode (JSON output)
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
from pathlib import Path

# Windows: force UTF-8 on stdout/stderr so rich's box-drawing chars don't crash cp1252
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from src.cli.client import NexusClient
from src.cli.commands import dispatch
from src.cli.completer import NexusCompleter
from src.cli.themes import THEMES, Theme


# ── Constants ────────────────────────────────────────────────────────

HISTORY_FILE = Path.home() / ".nexus" / "console_history"
VERSION = "2.0"

BANNER = r"""
[bold cyan]╔═══════════════════════════════════════════════════╗
║  ◆ NEXUS Console v{ver}                              ║
║  SuperNEXUS AI Platform — Terminal Mode            ║
╚═══════════════════════════════════════════════════╝[/]
"""

# ── Status Bar ───────────────────────────────────────────────────────

class StatusPoller:
    """Background thread that polls /api/status every N seconds."""

    def __init__(self, client: NexusClient, interval: float = 10.0):
        self.client = client
        self.interval = interval
        self._data: dict = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)

    def start(self):
        self._poll_once()  # Immediate first poll
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _poll_once(self):
        try:
            data = self.client.status()
            with self._lock:
                self._data = data
        except Exception:
            pass

    def _poll_loop(self):
        while not self._stop.wait(self.interval):
            self._poll_once()

    @property
    def data(self) -> dict:
        with self._lock:
            return dict(self._data)

    def toolbar_text(self, theme: Theme) -> str:
        d = self.data
        if not d:
            return "◆ NEXUS │ connecting..."

        online = d.get("online", False)
        status = "● ONLINE" if online else "○ OFFLINE"
        v = d.get("version", "?")

        # Model
        director = d.get("director", {})
        model = director.get("model", "?")

        # Agents count
        engines = d.get("engines", {})
        online_count = sum(1 for s in engines.values() if s == "online")
        total_count = len(engines)

        # Cerebro
        cerebro = d.get("cerebro", {})
        knowledge = cerebro.get("conocimientos", "?")

        parts = [
            f"◆ NEXUS v{v}",
            status,
            model,
            f"▲ {online_count}/{total_count} engines",
            f"🧠 {knowledge}",
        ]
        return " │ ".join(parts)


# ── Prompt Styling ───────────────────────────────────────────────────

def make_prompt_style(theme: Theme) -> Style:
    """Create prompt_toolkit Style from theme colors."""
    c = theme.colors
    return Style.from_dict({
        "prompt": c.primary,
        "prompt.separator": c.accent,
        "prompt.path": c.success,
        "prompt.arrow": c.primary,
        "bottom-toolbar": f"bg:{c.background} {c.muted}",
        "bottom-toolbar.text": c.info,
        "completion-menu.completion": f"bg:#1a2030 {c.foreground}",
        "completion-menu.completion.current": f"bg:{c.primary} #000000",
        "completion-menu.meta.completion": f"bg:#1a2030 {c.muted}",
        "completion-menu.meta.completion.current": f"bg:{c.primary} #000000",
    })


def make_prompt_message(project: str = "") -> list:
    """Build the prompt fragments."""
    proj = project or os.path.basename(os.getcwd())
    return [
        ("class:prompt", "nexus"),
        ("class:prompt.separator", ":"),
        ("class:prompt.path", proj),
        ("class:prompt.arrow", " ❯ "),
    ]


# ── Key Bindings ─────────────────────────────────────────────────────

def make_keybindings() -> KeyBindings:
    kb = KeyBindings()

    @kb.add("f1")
    def _help(event):
        """Show help."""
        event.current_buffer.text = "/help"
        event.current_buffer.validate_and_handle()

    @kb.add("f5")
    def _refresh(event):
        """Force status refresh."""
        event.current_buffer.text = "/status"
        event.current_buffer.validate_and_handle()

    @kb.add("c-l")
    def _clear(event):
        """Clear screen."""
        event.current_buffer.text = "/clear"
        event.current_buffer.validate_and_handle()

    return kb


# ── Pipe (batch) Mode ────────────────────────────────────────────────

def run_pipe_mode(client: NexusClient):
    """Non-interactive mode: read commands from stdin, output JSON."""
    console = Console(highlight=False, force_terminal=False, legacy_windows=False)
    for line in sys.stdin:
        line = line.lstrip("﻿").strip()
        if not line:
            continue
        result = dispatch(line, client, console)
        if result == "exit":
            break


# ── Interactive REPL ─────────────────────────────────────────────────

def run_interactive(client: NexusClient, theme_name: str = "nexus"):
    """Main interactive REPL loop."""
    theme = THEMES.get(theme_name, THEMES["nexus"])
    console = Console(highlight=False, force_terminal=True)

    # Banner
    console.print(BANNER.format(ver=VERSION))

    # Quick status check
    try:
        status = client.status()
        if status.get("online"):
            console.print(f"  [green]✓[/] Connected to [cyan]{client.base_url}[/]")
            model = status.get("director", {}).get("model", "?")
            console.print(f"  [green]✓[/] Model: [bold]{model}[/]")
        else:
            console.print(f"  [yellow]⚠[/] Server at {client.base_url} is offline")
    except Exception:
        console.print(f"  [red]✗[/] Cannot reach {client.base_url}")
    console.print()

    # Components
    completer = NexusCompleter()
    status_poller = StatusPoller(client)
    status_poller.start()

    # Load dynamic completions
    try:
        gems = client.gemas()
        if "gems" in gems:
            names = []
            for g in gems["gems"]:
                names.append(g.get("name", str(g)) if isinstance(g, dict) else str(g))
            completer.set_agents(names)
    except Exception:
        pass

    # Prompt session
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    session: PromptSession = PromptSession(
        message=make_prompt_message(),
        style=make_prompt_style(theme),
        completer=completer,
        complete_while_typing=True,
        history=FileHistory(str(HISTORY_FILE)),
        key_bindings=make_keybindings(),
        bottom_toolbar=lambda: HTML(
            f"<b>{status_poller.toolbar_text(theme)}</b>"
        ),
        multiline=False,
        mouse_support=False,
        refresh_interval=0.5,
    )

    # Main loop
    while True:
        try:
            text = session.prompt()
        except KeyboardInterrupt:
            continue  # Ctrl+C clears line
        except EOFError:
            break  # Ctrl+D exits

        result = dispatch(text, client, console)

        if result == "exit":
            break
        elif result == "clear":
            console.clear()
            console.print(BANNER.format(ver=VERSION))
        elif result and result.startswith("theme:"):
            new_theme = result.split(":", 1)[1].strip()
            if new_theme in THEMES:
                theme = THEMES[new_theme]
                session.style = make_prompt_style(theme)
                console.print(f"[green]✓ Theme: {new_theme}[/]")
            else:
                console.print(f"[red]✗ Unknown theme: {new_theme}[/]")

    # Cleanup
    status_poller.stop()
    console.print("\n[dim]◆ NEXUS Console terminated.[/]")


# ── Entry Point ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="nexus-console",
        description="NEXUS Console — Professional TUI REPL",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("NEXUS_HOST", "http://localhost:9000"),
        help="API server URL",
    )
    parser.add_argument(
        "--theme", "-t",
        default=os.environ.get("NEXUS_THEME", "nexus"),
        choices=list(THEMES.keys()),
        help="UI theme (default: nexus)",
    )
    args = parser.parse_args()
    client = NexusClient(args.host)

    # Pipe mode if stdin is not a TTY
    if not sys.stdin.isatty():
        run_pipe_mode(client)
        return

    run_interactive(client, theme_name=args.theme)


if __name__ == "__main__":
    main()
