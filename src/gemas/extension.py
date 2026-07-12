"""
GemaExtension — Extension plugin system for SuperNEXUS gemas.

Portado de Confucius (Meta) con adaptaciones para SuperNEXUS:
  - Integra con GemaBase existente (execute() + manifest)
  - Tag-based lifecycle hooks como Confucius Extension
  - Sin dependencia de LangChain
  - XMLOutputParser para structured LLM I/O

Jerarquía:
    GemaBase (existente, gemas_core)
      └── GemaExtension (nuevo) — añade lifecycle hooks + tags + xml parser
            ├── CodeGema
            ├── ScholarGema
            └── ...

Cada GemaExtension:
  1. Declara tags XML que entiende (tag_vocabulary)
  2. Produce descripciones automáticas para system prompt
  3. Se engancha en 8+ puntos del lifecycle
  4. Puede detener/continuar el loop via raise Interruption / Termination
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import bs4

from src.gemas_core.base import GemaBase
from src.core.extension_pipeline import ExtensionPipeline

from .tags import Tag, TagLike, Example, Examples
from .xml_output_parser import XMLOutputParser, XMLOutput

logger = logging.getLogger(__name__)


class GemaInterruption(Exception):
    """Gema solicita otra iteración del orchestrator con mensajes adicionales."""
    def __init__(self, messages: List[Dict[str, str]] | str | None = None):
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        self.messages: List[Dict[str, str]] = messages or []


class GemaTermination(Exception):
    """Gema indica que el loop debe terminar (éxito o error fatal)."""
    pass


@dataclass
class GemaContext:
    """Contexto compartido entre hooks del lifecycle de una gema.

    Similar a AnalectRunContext (Confucius) pero adaptado a SuperNEXUS:
      - session_id: sesión activa
      - messages: historial de mensajes (rol + contenido)
      - artifacts: dict de artefactos producidos por la gema
      - metadata: metadatos arbitrarios para hooks
      - extension_pipeline: pipeline global para logging/auditoría
    """
    session_id: str = ""
    task: str = ""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    pipeline: Optional[ExtensionPipeline] = None
    _interrupted: bool = False
    _terminated: bool = False


class Hook(ABC):
    """Hook individual — punto de extensión en el lifecycle."""
    name: str

    @abstractmethod
    async def on_input(self, task: str, context: GemaContext) -> Tuple[str, GemaContext]:
        return task, context

    @abstractmethod
    async def on_memory(self, query: str, context: GemaContext) -> Tuple[str, GemaContext]:
        return query, context

    @abstractmethod
    async def on_context_build(self, context_data: Dict, context: GemaContext) -> Tuple[Dict, GemaContext]:
        return context_data, context

    @abstractmethod
    async def on_invoke_llm(self, messages: List[Dict], context: GemaContext) -> Tuple[List[Dict], GemaContext]:
        return messages, context

    @abstractmethod
    async def on_llm_response(self, response: str, context: GemaContext) -> Tuple[str, GemaContext]:
        return response, context

    @abstractmethod
    async def on_tool_call(self, tool_name: str, params: Dict, context: GemaContext) -> Tuple[str, Dict, GemaContext]:
        return tool_name, params, context

    @abstractmethod
    async def on_tool_result(self, result: Any, context: GemaContext) -> Tuple[Any, GemaContext]:
        return result, context

    @abstractmethod
    async def on_tag(self, tag: bs4.Tag, context: GemaContext) -> Optional[bool]:
        """Procesa un tag del XML output del LLM.
        Returns: True si el tag fue manejado, None si no."""
        return None

    @abstractmethod
    async def on_llm_output(self, text: str, context: GemaContext) -> str:
        """Post-procesa el output plano del LLM (antes de parsear tags)."""
        return text

    @abstractmethod
    async def on_process_complete(self, context: GemaContext) -> None:
        """Callback al completar el ciclo de procesamiento.
        Raise GemaInterruption para continuar, GemaTermination para terminar."""
        pass


class GemaExtension(GemaBase, ABC):
    """Gema con extension lifecycle: tags + hooks + XML parser.

    Cualquier gema que herede de GemaExtension obtiene:
      - tag_vocabulary → system prompt descriptions automáticas
      - XMLOutputParser para parsear respuestas estructuradas
      - 10 hooks de lifecycle para interceptar/transformar datos
      - Interruption/Termination para control de flujo
    """

    name: str = ""
    description: str = ""
    category: str = "general"
    tag_vocabulary: List[TagLike] = field(default_factory=list)
    examples: List[TagLike] = field(default_factory=list)
    format_instructions: Optional[str] = None
    root_tag: str = "response"
    included_in_system_prompt: bool = True
    stop_sequences: List[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.tag_vocabulary is None:
            self.tag_vocabulary = []
        if self.examples is None:
            self.examples = []
        if self.stop_sequences is None:
            self.stop_sequences = ["</" + self.root_tag + ">"]
        self._xml_parser = XMLOutputParser(root_tag=self.root_tag)

    async def build_system_prompt_section(self) -> str:
        """Genera la sección de system prompt para esta gema.

        Incluye:
          1. Role description
          2. Tag vocabulary (tags que la gema entiende)
          3. Format instructions
          4. Examples
        """
        tags = []
        if self.tag_vocabulary:
            tags.append(Tag(name="available_tags", contents=self.tag_vocabulary))
        if self.format_instructions:
            tags.append(Tag(name="format_instructions", contents=self.format_instructions))
        else:
            tags.append(Tag(name="format_instructions", contents=self._xml_parser.get_format_instructions()))
        if self.examples:
            tags.append(Examples(contents=[Example(contents=ex) for ex in self.examples]))

        if not tags:
            return ""

        soup_tag = Tag(
            name=self.root_tag,
            contents=tags,
        )
        return soup_tag.prettify()

    async def on_input(self, task: str, context: GemaContext) -> Tuple[str, GemaContext]:
        return task, context

    async def on_memory(self, query: str, context: GemaContext) -> Tuple[str, GemaContext]:
        return query, context

    async def on_context_build(self, context_data: Dict, context: GemaContext) -> Tuple[Dict, GemaContext]:
        return context_data, context

    async def on_invoke_llm(self, messages: List[Dict], context: GemaContext) -> Tuple[List[Dict], GemaContext]:
        return messages, context

    async def on_llm_response(self, response: str, context: GemaContext) -> Tuple[str, GemaContext]:
        return response, context

    async def on_llm_output(self, text: str, context: GemaContext) -> str:
        return text

    async def on_tag(self, tag: bs4.Tag, context: GemaContext) -> Optional[bool]:
        return None

    async def on_tool_call(self, tool_name: str, params: Dict, context: GemaContext) -> Tuple[str, Dict, GemaContext]:
        return tool_name, params, context

    async def on_tool_result(self, result: Any, context: GemaContext) -> Tuple[Any, GemaContext]:
        return result, context

    async def on_process_complete(self, context: GemaContext) -> None:
        pass

    async def parse_response(self, text: str) -> XMLOutput:
        """Parsea la respuesta del LLM usando XMLOutputParser."""
        return await self._xml_parser.aparse(text)

    def extract_tag(self, text: str, tag_name: str) -> Optional[str]:
        """Extrae contenido de un tag específico del XML."""
        return self._xml_parser.extract_tag(text, tag_name)

    def extract_all_tags(self, text: str, tag_name: str) -> List[str]:
        """Extrae contenido de todas las ocurrencias de un tag."""
        return self._xml_parser.extract_all_tags(text, tag_name)

    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        """Override de GemaBase.execute() con lifecycle hooks.

        Flujo:
          1. on_input → intercepta/modifica task
          2. build_system_prompt_section → genera XML tags
          3. invoke LLM con system prompt + task
          4. on_llm_output → post-procesa respuesta
          5. parse_response → XMLOutput
          6. on_tag → dispatch por tag
          7. on_process_complete → continuar o terminar
          8. Retorna Dict con resultado estructurado
        """
        gema_ctx = GemaContext(task=task)

        task, gema_ctx = await self.on_input(task, gema_ctx)
        response = await self._call_llm(task, context, gema_ctx)
        response, gema_ctx = await self.on_llm_response(response, gema_ctx)
        output = await self.on_llm_output(response, gema_ctx)

        try:
            parsed = await self.parse_response(output)
            for tag in parsed.soup.find_all(True):
                if tag.name != self.root_tag:
                    handled = await self.on_tag(tag, gema_ctx)
            await self.on_process_complete(gema_ctx)
        except GemaTermination:
            pass
        except GemaInterruption as exc:
            gema_ctx._interrupted = True
            gema_ctx.messages.extend(exc.messages)

        return {
            "success": True,
            "gema": self.name,
            "task": task,
            "output": output,
            "interrupted": gema_ctx._interrupted,
            "artifacts": gema_ctx.artifacts,
        }

    async def _call_llm(self, task: str, context: str, gema_ctx: GemaContext) -> str:
        """LLM call básica — override en subclases para diferentes backends."""
        prompt = task
        if context:
            prompt = f"{context}\n\n---\nTarea: {task}"
        # Subclases implementan la llamada real al LLM según su backend
        return prompt


class GemaOrchestrator:
    """Orchestra múltiples GemaExtensions en un pipeline.

    Similar a BaseOrchestrator (Confucius) pero adaptado a SuperNEXUS:
      - Mantiene lista de extensiones (gemas) registradas
      - Cada extensión recibe el mismo input y procesa su tag vocabulary
      - Soporta Interruption → recursión y Termination → corte
    """

    def __init__(self, extensions: Optional[List[GemaExtension]] = None):
        self.extensions: List[GemaExtension] = extensions or []
        self._pipeline = ExtensionPipeline("gema-orchestrator")

    def register(self, ext: GemaExtension):
        self.extensions.append(ext)
        logger.info(f"Gema registrada: {ext.name}")

    async def build_system_prompt(self) -> str:
        """Construye el system prompt combinando todas las gemas registradas."""
        sections = []
        for ext in self.extensions:
            if ext.included_in_system_prompt:
                section = await ext.build_system_prompt_section()
                if section:
                    sections.append(section)
        return "\n".join(sections)

    async def dispatch_tags(self, text: str, context: GemaContext) -> None:
        """Dispatcha tags XML a las extensiones registradas."""
        parser = XMLOutputParser()
        output = await parser.aparse(text)
        for tag in output.soup.find_all(True):
            if tag.name == parser.root_tag:
                continue
            for ext in self.extensions:
                handled = await ext.on_tag(tag, context)
                if handled:
                    break
