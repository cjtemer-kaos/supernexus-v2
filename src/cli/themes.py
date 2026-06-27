from dataclasses import dataclass, field

@dataclass
class Colors:
    primary: str = "#00aaff"
    secondary: str = "#4a9eff"
    accent: str = "#61afef"
    success: str = "#98c379"
    warning: str = "#e5c07b"
    error: str = "#e06c75"
    info: str = "#61afef"
    muted: str = "#5c6370"
    background: str = "#1e1e2e"
    foreground: str = "#cdd6f4"
    highlight: str = "#f5c2e7"

@dataclass
class Icons:
    spinner: str = "dots"
    success: str = "\u2713"
    error: str = "\u2717"
    warning: str = "\u26a0"
    info: str = "\u25cf"
    agent: str = "\u25c6"
    arrow: str = "\u2192"
    star: str = "\u2605"

@dataclass
class Theme:
    name: str = "nexus"
    colors: Colors = field(default_factory=Colors)
    icons: Icons = field(default_factory=Icons)
    border_style: str = "rounded"
    table_border: str = "SIMPLE"

NEXUS_THEME = Theme()

DARK_THEME = Theme(
    name="dark",
    colors=Colors(
        primary="#bb9af7", secondary="#7aa2f7", accent="#9ece6a",
        success="#9ece6a", warning="#e0af68", error="#f7768e",
        info="#7aa2f7", muted="#414868", background="#1a1b26",
        foreground="#c0caf5", highlight="#ff9e64",
    ),
    border_style="single",
    table_border="SIMPLE",
)

CYBERPUNK_THEME = Theme(
    name="cyberpunk",
    colors=Colors(
        primary="#00ff41", secondary="#bf00ff", accent="#00ffff",
        success="#00ff41", warning="#ffff00", error="#ff0054",
        info="#00ffff", muted="#1a1a2e", background="#0d0d0d",
        foreground="#00ff41", highlight="#ff00ff",
    ),
    icons=Icons(
        spinner="dots", success="◆", error="◌", warning="◇",
        info="○", agent="◎", arrow="⟶", star="◇",
    ),
    border_style="double",
    table_border="HEAVY",
)

MINIMAL_THEME = Theme(
    name="minimal",
    colors=Colors(
        primary="#ffffff", secondary="#cccccc", accent="#999999",
        success="#00ff00", warning="#ffff00", error="#ff0000",
        info="#cccccc", muted="#666666", background="#000000",
        foreground="#ffffff", highlight="#ffffff",
    ),
    icons=Icons(
        spinner="line", success="+", error="!", warning="?",
        info=".", agent=">", arrow="->", star="*",
    ),
    border_style="none",
    table_border="SIMPLE",
)

THEMES = {
    "nexus": NEXUS_THEME,
    "dark": DARK_THEME,
    "cyberpunk": CYBERPUNK_THEME,
    "minimal": MINIMAL_THEME,
}
