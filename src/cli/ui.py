from __future__ import annotations


from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.box import SIMPLE

from src.cli.themes import Theme, THEMES, NEXUS_THEME


import sys


class NexusUI:
    def __init__(self, style: str = "nexus"):
        self.console = Console(legacy_windows=False, highlight=False, force_terminal=True)
        self.theme: Theme = THEMES.get(style, NEXUS_THEME)
        self._unicode = sys.stdout.encoding.lower() not in ("cp1252", "ascii", "ansi")
        self._spinner = None
        self._progress: Progress | None = None

    def set_theme(self, name: str):
        self.theme = THEMES.get(name, NEXUS_THEME)

    def _c(self, color: str) -> str:
        return getattr(self.theme.colors, color, color)

    def _box(self) -> str:
        return self.theme.table_border

    def print(self, text: str = "", style: str = "", end: str = "\n"):
        self.console.print(text, style=style, end=end)

    def _icon(self, icon_name: str) -> str:
        icon = getattr(self.theme.icons, icon_name, "")
        if not self._unicode:
            return {"success": "+", "error": "!", "warning": "?", "info": "o", "agent": "#", "arrow": "->", "star": "*"}.get(icon_name, icon)
        return icon

    def info(self, msg: str):
        c = self._c("info")
        self.console.print(f"  [{c}]{self._icon('info')}[/] {msg}")

    def success(self, msg: str):
        c = self._c("success")
        self.console.print(f"  [{c}]{self._icon('success')}[/] {msg}")

    def warning(self, msg: str):
        c = self._c("warning")
        self.console.print(f"  [{c}]{self._icon('warning')}[/] {msg}")

    def error(self, msg: str):
        c = self._c("error")
        self.console.print(f"  [{c}]{self._icon('error')}[/] {msg}")

    def header(self, text: str):
        c = self._c("primary")
        bar = "===" if not self._unicode else "\u2550\u2550\u2550"
        self.console.print(f"\n[{c}]{bar} {text} {bar}[/]")

    def subheader(self, text: str):
        c = self._c("secondary")
        self.console.print(f"  [{c}]{text}[/]")

    def panel(self, text: str, title: str = "", style: str = ""):
        s = style or self._c("primary")
        self.console.print(Panel(
            text, title=title, border_style=s,
        ))

    def md(self, text: str):
        self.console.print(Markdown(text))

    def table(self, headers: list[str], rows: list[list[str]], title: str = ""):
        t = Table(title=title, box=SIMPLE)
        for h in headers:
            t.add_column(h, style=self._c("info"), no_wrap=True)
        for row in rows:
            t.add_row(*row)
        self.console.print(t)

    def thinking(self, msg: str = "Thinking..."):
        c = self._c("info")
        self._spinner = Progress(
            SpinnerColumn(spinner_name=self.theme.icons.spinner),
            TextColumn(f"[{c}]{msg}[/]"),
            transient=True,
        )
        self._spinner.__enter__()

    def stop_thinking(self):
        if self._spinner:
            self._spinner.__exit__(None, None, None)
            self._spinner = None

    def render_json(self, data: dict) -> str:
        return Syntax(
            __import__("json").dumps(data, indent=2, ensure_ascii=False),
            "json",
            theme="monokai",
            line_numbers=False,
        )

    def status_line(self, items: list[tuple[str, str]]):
        sep = f" {self._icon('arrow')} "
        parts = []
        for label, val in items:
            parts.append(f"[{self._c('muted')}]{label}:[/] {val}")
        line = sep.join(parts)
        self.console.print(f"[dim]{line}[/dim]")
