"""
gemas — Extension plugin system based on Confucius patterns.

Módulos:
    tags.py           — XML Tag model for structured LLM I/O
    xml_output_parser.py — Parse structured LLM responses into BeautifulSoup
    extension.py      — GemaExtension: GemaBase + lifecycle hooks + tags + XML
"""

from .tags import (
    Tag,
    TagLike,
    Example,
    Examples,
    Thinking,
    ToolUse,
    AssistantResponse,
    UserQuery,
    unescape,
    unescaped_tag_content,
)
from .xml_output_parser import XMLOutputParser, XMLOutput
from .extension import (
    GemaExtension,
    GemaOrchestrator,
    GemaContext,
    GemaInterruption,
    GemaTermination,
)

__all__ = [
    "Tag",
    "TagLike",
    "Example",
    "Examples",
    "Thinking",
    "ToolUse",
    "AssistantResponse",
    "UserQuery",
    "unescape",
    "unescaped_tag_content",
    "XMLOutputParser",
    "XMLOutput",
    "GemaExtension",
    "GemaOrchestrator",
    "GemaContext",
    "GemaInterruption",
    "GemaTermination",
]
