"""
AI Tools - Herramientas de IA para SuperNEXUS v2.0

Las IAs son HERRAMIENTAS, no el cerebro. NEXUS es el cerebro.
Cada modelo tiene un rol específico, prompt específico, y se invoca solo cuando se necesita.

Modelo por defecto: qwen2.5-coder:7b (ligero, estable, no delira)
"""

import logging
import os
import re
import glob as glob_module
import subprocess
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from src.core.ollama import OllamaClient
from src.core.schema_sanitizer import SchemaSanitizer

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AITool:
    """Una herramienta de IA específica"""
    name: str
    model: str
    role: str
    system_prompt: str
    tags: List[str]
    max_tokens: int = 2048
    temperature: float = 0.7
    call_count: int = 0
    total_tokens: int = 0
    last_used: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "model": self.model,
            "role": self.role,
            "tags": self.tags,
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "last_used": self.last_used,
        }


class AIToolsRegistry:
    """
    Registro de herramientas de IA.
    
    NEXUS es el cerebro. Estas son sus herramientas.
    Cada herramienta tiene un system prompt específico que la mantiene enfocada.
    """

    # System prompts optimizados con técnicas de Prompt Engineering (NirDiamant)
    # Técnicas aplicadas: Role-playing, Context-Instruction-Format, Negative constraints, Examples
    SYSTEM_PROMPTS = {
        "qwen_coder": """<role>Eres una herramienta de código de NEXUS IA.</role>
<task>Tu ÚNICA función es escribir, revisar o modificar código cuando NEXUS te lo pida.</task>
<rules>
- Responde SOLO con código o explicaciones técnicas breves
- NO actúes como asistente conversacional
- NO olvides que eres una herramienta de NEXUS
- Si no entiendes la tarea, di "NECESITO MÁS CONTEXTO"
- Usa el formato de código apropiado para el lenguaje solicitado
- Incluye comentarios solo cuando sea necesario para claridad
- Prefiere código limpio y legible sobre código clever
</rules>
<format>
- Usa bloques de código con lenguaje especificado
- Si hay errores, explica brevemente la causa y solución
- No incluyas saludos ni despedidas
</format>""",

        "llama_chat": """Eres DirectorNexus. Responde en español. Sé directo y útil.""",

        "deepseek_reason": """<role>Eres una herramienta de razonamiento de NEXUS IA.</role>
<task>Tu función es analizar problemas complejos y proporcionar soluciones lógicas.</task>
<rules>
- Piensa paso a paso antes de responder
- Proporciona análisis estructurado
- NO olvides que eres una herramienta de NEXUS IA
- Identifica suposiciones y limitaciones
- Proporciona múltiples perspectivas cuando sea relevante
- Considera edge cases y escenarios alternativos
</rules>
<format>
- Estructura: Análisis → Opciones → Recomendación
- Usa viñetas para claridad
- Indica nivel de confianza cuando sea apropiado
</format>""",

        "qwen_vision": """<role>Eres una herramienta de visión de NEXUS IA.</role>
<task>Tu función es analizar imágenes y screenshots que NEXUS te envíe.</task>
<rules>
- Describe lo que ves de forma objetiva
- Identifica elementos UI, texto, errores visuales
- NO inventes contenido que no está en la imagen
- Sé específico sobre posiciones y colores
- Si la imagen no es clara, indícalo
- Prioriza información relevante sobre detalles triviales
</rules>
<format>
- Descripción general primero
- Detalles específicos después
- Menciona texto visible si existe
</format>""",

        "nemotron_fast": """<role>Eres una herramienta de respuestas rápidas de NEXUS IA.</role>
<task>Tu función es responder consultas simples de forma muy breve.</task>
<rules>
- Máximo 2-3 oraciones
- Directo al punto
- NO olvides que eres parte de NEXUS IA
- Sin explicaciones innecesarias
- Ideal para resúmenes y confirmaciones
</rules>
<format>
- Una respuesta directa
- Sin preámbulos
- Sin conclusiones innecesarias
</format>""",

        "gemma_creative": """<role>Eres una herramienta creativa de NEXUS IA.</role>
<task>Tu función es generar contenido creativo: textos, ideas, nombres, descripciones.</task>
<rules>
- Sé original e imaginativo
- Adapta el tono según lo solicitado
- NO olvides que eres una herramienta de NEXUS IA
- Proporciona múltiples opciones cuando sea útil
- Mantén la coherencia con el contexto dado
- Evita clichés y frases hechas
</rules>
<format>
- Presenta opciones numeradas cuando aplique
- Incluye variaciones de estilo
- Mantén consistencia temática
</format>""",

        "scholar_research": """<role>Eres una herramienta de investigación de NEXUS IA.</role>
<task>Tu función es buscar, analizar y sintetizar información.</task>
<rules>
- Cita fuentes cuando sea posible
- Distingue hechos de opiniones
- NO olvides que eres parte de NEXUS IA
- Proporciona información estructurada
- Indica el nivel de confianza de la información
- Reconoce limitaciones del conocimiento
</rules>
<format>
- Resumen ejecutivo primero
- Detalles con fuentes
- Conclusiones al final
- Indica incertidumbre cuando exista
</format>""",

        "multimedia_design": """<role>Eres una herramienta de diseño multimedia de NEXUS IA.</role>
<task>Tu función es generar prompts para Veo 3.1, describir escenas, y planificar contenido audiovisual.</task>
<rules>
- Genera prompts detallados para generación de video
- Describe escenas con precisión visual (iluminación, ángulos, movimiento)
- Estructura guiones y storyboards
- NO olvides que eres una herramienta de NEXUS IA
- Responde en formato JSON cuando se solicite
- Incluye detalles técnicos (resolución, frame rate, estilo)
</rules>
<format>
- Prompt estructurado: sujeto + acción + entorno + estilo técnico
- Storyboard: escena por escena
- JSON cuando se solicite estructura
</format>""",

        "music_generator": """<role>Eres una herramienta de generación musical de NEXUS IA.</role>
<task>Tu función es crear descripciones de audio, prompts para generación musical, y estructurar composiciones.</task>
<rules>
- Describe estilos musicales con precisión
- Genera prompts para herramientas de generación de audio
- Estructura composiciones (intro, verso, coro, puente, outro)
- NO olvides que eres una herramienta de NEXUS IA
- Proporciona detalles técnicos (BPM, tonalidad, instrumentos)
- Considera la progresión emocional de la pieza
</rules>
<format>
- Estructura: BPM + Tonalidad + Instrumentación + Estructura
- Prompts descriptivos para generación
- Timeline cuando aplique
</format>""",

        "prompt_engineer": """<role>Eres una herramienta de ingeniería de prompts de NEXUS IA.</role>
<task>Tu función es optimizar, comprimir y estructurar prompts para máxima efectividad.</task>
<rules>
- Reduce tokens sin perder significado
- Estructura prompts con contexto, instrucciones y formato de salida
- Identifica ambigüedades y las resuelve
- NO olvides que eres una herramienta de NEXUS IA
- Proporciona versiones optimizadas y explicación de cambios
- Aplica técnicas: role-playing, few-shot, chain-of-thought cuando sea útil
</rules>
<format>
- Prompt original → Prompt optimizado
- Explicación de cambios
- Métricas de mejora (tokens ahorrados, claridad)
</format>""",

        "producer_marketing": """<role>Eres una herramienta de producción y marketing de NEXUS IA.</role>
<task>Tu función es planificar campañas, generar contenido de marketing, y automatizar tareas.</task>
<rules>
- Crea calendarios de contenido
- Genera copy para redes sociales
- Planifica secuencias de automatización
- NO olvides que eres una herramienta de NEXUS IA
- Responde con planes accionables y métricas
- Considera audiencia objetivo y tono de marca
</rules>
<format>
- Plan estructurado con fechas
- Copy listo para publicar
- Métricas objetivo y KPIs
- Automatizaciones sugeridas
</format>""",
    }

    def __init__(self, ollama: Optional[OllamaClient] = None):
        self.ollama = ollama or OllamaClient()
        self.tools: Dict[str, AITool] = {}
        self.default_model = "qwen2.5:0.5b"
        # Builtin tools for file access and command execution
        from src.tools.builtin import WorkspaceTools, ExecuteTools
        self.workspace = WorkspaceTools()
        self.executor = ExecuteTools()
        self._load_tools()

    def _load_tools(self):
        """Carga todas las herramientas de IA disponibles"""
        tools_config = [
            AITool(
                name="qwen_coder",
                model="qwen2.5:0.5b",
                role="coding",
                system_prompt=self.SYSTEM_PROMPTS["qwen_coder"],
                tags=["code", "programming", "debug", "refactor", "script"],
                temperature=0.3,
            ),
            AITool(
                name="nemotron_chat",
                model="qwen2.5:0.5b",
                role="chat",
                system_prompt=self.SYSTEM_PROMPTS["llama_chat"],
                tags=["chat", "general", "question", "explain", "help"],
                temperature=0.7,
            ),
            AITool(
                name="deepseek_reason",
                model="qwen2.5:0.5b",
                role="reasoning",
                system_prompt=self.SYSTEM_PROMPTS["deepseek_reason"],
                tags=["analyze", "plan", "design", "think", "reason", "complex"],
                temperature=0.5,
            ),
            AITool(
                name="qwen_vision",
                model="qwen2.5:0.5b",
                role="vision",
                system_prompt=self.SYSTEM_PROMPTS["qwen_vision"],
                tags=["vision", "screenshot", "image", "screen", "visual"],
                temperature=0.3,
            ),
            AITool(
                name="nemotron_fast",
                model="qwen2.5:0.5b",
                role="fast",
                system_prompt=self.SYSTEM_PROMPTS["nemotron_fast"],
                tags=["quick", "simple", "summary", "confirm", "status"],
                temperature=0.5,
            ),
            AITool(
                name="gemma_creative",
                model="gemma4:latest",
                role="creative",
                system_prompt=self.SYSTEM_PROMPTS["gemma_creative"],
                tags=["creative", "write", "content", "name", "idea", "story"],
                temperature=0.9,
            ),
            AITool(
                name="scholar_research",
                model="deepseek-r1:8b",
                role="research",
                system_prompt=self.SYSTEM_PROMPTS["scholar_research"],
                tags=["research", "search", "investigate", "learn", "study"],
                temperature=0.5,
            ),
            # Nuevas herramientas multimedia
            AITool(
                name="multimedia_design",
                model="qwen2.5-coder:7b",
                role="multimedia",
                system_prompt=self.SYSTEM_PROMPTS["multimedia_design"],
                tags=["design", "video", "scene", "veo", "storyboard", "prompt_video", "ui", "ux", "multimedia"],
                temperature=0.8,
                max_tokens=4096,
            ),
            AITool(
                name="music_generator",
                model="gemma4:latest",
                role="music",
                system_prompt=self.SYSTEM_PROMPTS["music_generator"],
                tags=["music", "audio", "sound", "voice", "composition", "bpm", "melody", "song"],
                temperature=0.9,
                max_tokens=4096,
            ),
            AITool(
                name="prompt_engineer",
                model="qwen2.5-coder:7b",
                role="prompt",
                system_prompt=self.SYSTEM_PROMPTS["prompt_engineer"],
                tags=["prompt", "token", "optimization", "compression", "structure", "context"],
                temperature=0.3,
                max_tokens=2048,
            ),
            AITool(
                name="producer_marketing",
                model="llama3.2:3b",
                role="producer",
                system_prompt=self.SYSTEM_PROMPTS["producer_marketing"],
                tags=["producer", "marketing", "schedule", "automation", "campaign", "social", "rcon", "rust"],
                temperature=0.7,
                max_tokens=3072,
            ),
        ]

        for tool in tools_config:
            self.tools[tool.name] = tool

        logger.info(f"AIToolsRegistry loaded {len(self.tools)} tools (default: {self.default_model})")

    def select_tool(self, task: str, gem: str = "auto") -> AITool:
        """
        Selecciona la herramienta de IA apropiada para la tarea.
        NEXUS decide qué herramienta usar según el tipo de tarea.
        """
        task_lower = task.lower()

        # Si se especificó una gem, usar su modelo asociado
        if gem != "auto":
            gem_to_tool = {
                "code": "qwen_coder",
                "coder": "qwen_coder",
                "engineer": "qwen_coder",
                "debugger": "qwen_coder",
                "devops": "qwen_coder",
                "tester": "qwen_coder",
                "optimizer": "qwen_coder",
                "architect": "deepseek_reason",
                "analyst": "deepseek_reason",
                "scholar": "scholar_research",
                "creative": "gemma_creative",
                "design": "multimedia_design",
                "vision": "qwen_vision",
                "music": "music_generator",
                "prompter": "prompt_engineer",
                "director": "nemotron_chat",
                "sage": "deepseek_reason",
                "biblioteca": "nemotron_chat",
                "trainer": "nemotron_chat",
                "security": "deepseek_reason",
                "opencode": "qwen_coder",
                "codex": "qwen_coder",
                "producer": "producer_marketing",
            }
            tool_name = gem_to_tool.get(gem, "qwen_coder")
            if tool_name in self.tools:
                return self.tools[tool_name]

        # Selección automática por keywords
        for tool in self.tools.values():
            if any(tag in task_lower for tag in tool.tags):
                return tool

        # Default: qwen_coder (estable, no delira)
        return self.tools.get("qwen_coder", list(self.tools.values())[0])

    async def execute(
        self,
        tool_name: str,
        user_message: str,
        context: str = "",
        images: Optional[List[str]] = None,
    ) -> Dict:
        """
        Ejecuta una herramienta de IA con un mensaje específico.
        La herramienta recibe un prompt acotado y devuelve un resultado estructurado.
        """
        tool = self.tools.get(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found", "available_tools": list(self.tools.keys())}

        # Construir mensajes con system prompt específico
        messages = [
            {"role": "system", "content": tool.system_prompt},
        ]

        # For chat tool, prepend identity directly to user message (more reliable for small models)
        final_message = user_message
        if tool_name == "nemotron_chat":
            final_message = f"Eres DirectorNexus. Responde como DirectorNexus.\n\n{user_message}"

        if context:
            messages.append({"role": "user", "content": f"Contexto:\n{context}"})

        messages.append({"role": "user", "content": final_message})

        start = datetime.now()

        try:
            # Para modelos de visión, usar endpoint especial
            if tool.role == "vision" and images:
                response = await self._call_vision_model(tool, messages, images)
            else:
                response = await self.ollama.chat(
                    model=tool.model,
                    messages=messages,
                    options={
                        "temperature": tool.temperature,
                        "num_predict": tool.max_tokens,
                    },
                )

            duration = (datetime.now() - start).total_seconds() * 1000
            content = response.get("message", {}).get("content", "")
            tokens_used = response.get("eval_count", 0) + response.get("prompt_eval_count", 0)

            # Actualizar stats
            tool.call_count += 1
            tool.total_tokens += tokens_used
            tool.last_used = datetime.now().isoformat()

            return {
                "success": True,
                "tool": tool_name,
                "model": tool.model,
                "content": content,
                "tokens_used": tokens_used,
                "duration_ms": duration,
                "done": response.get("done", False),
            }

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "success": False,
                "tool": tool_name,
                "error": str(e),
                "fallback": "NEXUS no pudo procesar esta solicitud con la herramienta seleccionada.",
            }

    async def _call_vision_model(
        self,
        tool: AITool,
        messages: List[Dict],
        images: List[str],
    ) -> Dict:
        """Llama a un modelo de visión con imágenes"""
        # Construir mensaje con imágenes para qwen2.5vl
        last_msg = messages[-1]
        content_parts = []
        
        for img_path in images:
            content_parts.append({"type": "image_url", "image_url": {"url": img_path}})
        
        content_parts.append({"type": "text", "text": last_msg["content"]})
        messages[-1] = {"role": "user", "content": content_parts}

        return await self.ollama.chat(
            model=tool.model,
            messages=messages,
            options={"temperature": tool.temperature},
        )

    async def quick_response(
        self,
        task: str,
        gem: str = "auto",
        context: str = "",
    ) -> Dict:
        """
        Respuesta rápida: selecciona herramienta y ejecuta.
        Este es el método principal que usa el DirectorNexus.
        """
        tool = self.select_tool(task, gem)
        return await self.execute(tool.name, task, context)

    def get_available_tools(self) -> List[Dict]:
        """Lista todas las herramientas disponibles"""
        return [t.to_dict() for t in self.tools.values()]

    def get_sanitized_tools(self, provider: str = "ollama") -> List[Dict]:
        """Lista herramientas con schemas sanitizados para el proveedor"""
        raw_tools = self.get_available_tools()
        return SchemaSanitizer.sanitize_tool_definitions(raw_tools, provider)

    def get_default_model(self) -> str:
        """Retorna el modelo por defecto"""
        return self.default_model

    def set_default_model(self, model: str):
        """Cambia el modelo por defecto"""
        if any(t.model == model for t in self.tools.values()):
            self.default_model = model
            logger.info(f"Default model changed to: {model}")
        else:
            logger.warning(f"Model {model} not found in tools registry")

    def get_stats(self) -> Dict:
        """Estadísticas de uso de herramientas"""
        total_calls = sum(t.call_count for t in self.tools.values())
        total_tokens = sum(t.total_tokens for t in self.tools.values())
        
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "tools": {name: t.to_dict() for name, t in self.tools.items()},
            "default_model": self.default_model,
        }

    async def _tool_view_file(self, path: str, offset: int = 0, limit: int = 2000) -> Dict:
        """Lee archivo con números de línea, paginación y detección de imágenes"""
        try:
            if not path:
                return {"error": "path is required"}
            
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            
            if not os.path.exists(path):
                dir_path = os.path.dirname(path)
                base = os.path.basename(path)
                suggestions = []
                if os.path.isdir(dir_path):
                    for entry in os.listdir(dir_path):
                        if base.lower() in entry.lower() or entry.lower() in base.lower():
                            suggestions.append(os.path.join(dir_path, entry))
                            if len(suggestions) >= 3:
                                break
                msg = f"File not found: {path}"
                if suggestions:
                    msg += f"\n\nDid you mean?\n" + "\n".join(suggestions)
                return {"error": msg}
            
            if os.path.isdir(path):
                return {"error": f"Path is a directory: {path}"}
            
            image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico'}
            ext = os.path.splitext(path)[1].lower()
            if ext in image_exts:
                return {"content": f"This is an image file ({ext}). Use vision model to process it.", "is_image": True, "image_type": ext}
            
            max_size = 250 * 1024
            file_size = os.path.getsize(path)
            if file_size > max_size:
                return {"error": f"File too large ({file_size} bytes). Max 250KB"}
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                all_lines = f.readlines()
            
            total_lines = len(all_lines)
            if offset < 0:
                offset = 0
            if limit <= 0:
                limit = 2000
            
            selected = all_lines[offset:offset + limit]
            content = "".join(selected)
            
            lines_with_nums = []
            for i, line in enumerate(selected):
                line_num = i + offset + 1
                lines_with_nums.append(f"{line_num:>6}|{line.rstrip()}")
            
            output = "<file>\n" + "\n".join(lines_with_nums) + "\n</file>"
            
            if offset + limit < total_lines:
                output += f"\n\n(File has {total_lines} total lines. Use offset={offset + limit} to read more.)"
            
            return {
                "success": True,
                "content": output,
                "path": path,
                "total_lines": total_lines,
                "lines_read": len(selected),
                "offset": offset,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_edit_file(self, path: str, old_string: str, new_string: str) -> Dict:
        """Reemplaza texto en archivo con validación de unicidad"""
        try:
            if not path:
                return {"error": "path is required"}
            
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            
            if not old_string and not new_string:
                return {"error": "old_string or new_string is required"}
            
            if not os.path.exists(path):
                if not old_string and new_string:
                    dir_path = os.path.dirname(path)
                    if dir_path and not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_string)
                    return {"success": True, "content": f"File created: {path}", "action": "create"}
                return {"error": f"File not found: {path}"}
            
            if os.path.isdir(path):
                return {"error": f"Path is a directory: {path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                old_content = f.read()
            
            if not old_string and new_string:
                return {"error": "old_string is required for existing files"}
            
            if old_string not in old_content:
                return {"error": "old_string not found in file. Must match exactly including whitespace and indentation"}
            
            if old_content.count(old_string) > 1:
                return {"error": "old_string appears multiple times. Provide more context to uniquely identify the instance"}
            
            new_content = old_content.replace(old_string, new_string, 1)
            
            if new_content == old_content:
                return {"error": "No changes. new_string is identical to current content"}
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            old_lines = old_string.count('\n') + 1
            new_lines = new_string.count('\n') + 1
            additions = max(0, new_lines - old_lines)
            removals = max(0, old_lines - new_lines)
            
            return {
                "success": True,
                "content": f"File edited: {path}",
                "path": path,
                "additions": additions,
                "removals": removals,
                "action": "edit",
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_patch_files(self, patch_text: str) -> Dict:
        """Aplica patch coordinado a múltiples archivos"""
        try:
            if not patch_text:
                return {"error": "patch_text is required"}
            
            lines = patch_text.strip().split('\n')
            if not patch_text.startswith('*** Begin Patch') or not patch_text.endswith('*** End Patch'):
                return {"error": "Patch must start with '*** Begin Patch' and end with '*** End Patch'"}
            
            current_file = None
            current_action = None
            file_changes: Dict[str, Dict] = {}
            pending_lines = []
            
            i = 0
            while i < len(lines):
                line = lines[i]
                i += 1
                
                if line.startswith('*** Begin Patch') or line.startswith('*** End Patch'):
                    continue
                
                if line.startswith('*** Update File:'):
                    if current_file and pending_lines:
                        file_changes[current_file] = {"action": current_action, "lines": pending_lines[:]}
                    current_file = line[len('*** Update File:'):].strip()
                    current_action = "update"
                    pending_lines = []
                elif line.startswith('*** Add File:'):
                    if current_file and pending_lines:
                        file_changes[current_file] = {"action": current_action, "lines": pending_lines[:]}
                    current_file = line[len('*** Add File:'):].strip()
                    current_action = "add"
                    pending_lines = []
                elif line.startswith('*** Delete File:'):
                    if current_file and pending_lines:
                        file_changes[current_file] = {"action": current_action, "lines": pending_lines[:]}
                    current_file = line[len('*** Delete File:'):].strip()
                    current_action = "delete"
                    pending_lines = []
                else:
                    if current_file:
                        pending_lines.append(line)
            
            if current_file and pending_lines:
                file_changes[current_file] = {"action": current_action, "lines": pending_lines[:]}
            
            changed_files = []
            total_additions = 0
            total_removals = 0
            
            for file_path, change in file_changes.items():
                if not os.path.isabs(file_path):
                    file_path = os.path.abspath(file_path)
                
                action = change["action"]
                patch_lines = change["lines"]
                
                if action == "delete":
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        changed_files.append(file_path)
                        total_removals += 1
                    continue
                
                if action == "add":
                    if os.path.exists(file_path):
                        return {"error": f"File already exists: {file_path}"}
                    dir_path = os.path.dirname(file_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                    content = "\n".join(l[1:] if l.startswith('+') else l for l in patch_lines if l.startswith('+'))
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    changed_files.append(file_path)
                    total_additions += content.count('\n') + 1
                    continue
                
                if action == "update":
                    if not os.path.exists(file_path):
                        return {"error": f"File not found: {file_path}"}
                    
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_content = f.read()
                    
                    old_lines_list = old_content.split('\n')
                    new_lines_list = []
                    skip_until_next_hunk = False
                    
                    j = 0
                    while j < len(patch_lines):
                        pl = patch_lines[j]
                        if pl.startswith('@@'):
                            j += 1
                            continue
                        if pl.startswith('-'):
                            j += 1
                            continue
                        if pl.startswith('+'):
                            new_lines_list.append(pl[1:])
                            j += 1
                            continue
                        if pl.startswith(' '):
                            new_lines_list.append(pl[1:])
                            j += 1
                            continue
                        new_lines_list.append(pl)
                        j += 1
                    
                    new_content = "\n".join(new_lines_list)
                    if not new_content.strip():
                        new_content = old_content
                        for pl in patch_lines:
                            if pl.startswith('-'):
                                removed = pl[1:]
                                if removed in new_content:
                                    new_content = new_content.replace(removed, '', 1)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    changed_files.append(file_path)
                    total_additions += max(0, sum(1 for l in patch_lines if l.startswith('+')))
                    total_removals += max(0, sum(1 for l in patch_lines if l.startswith('-')))
            
            result = f"Patch applied. {len(changed_files)} files changed, {total_additions} additions, {total_removals} removals"
            return {
                "success": True,
                "content": result,
                "files_changed": changed_files,
                "additions": total_additions,
                "removals": total_removals,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_grep(self, pattern: str, path: str = "", include: str = "", literal: bool = False) -> Dict:
        """Busca contenido en archivos usando regex o texto literal"""
        try:
            if not pattern:
                return {"error": "pattern is required"}
            
            search_path = path if path else os.getcwd()
            if not os.path.isabs(search_path):
                search_path = os.path.abspath(search_path)
            
            if not os.path.isdir(search_path):
                return {"error": f"Directory not found: {search_path}"}
            
            search_pattern = re.escape(pattern) if literal else pattern
            
            try:
                re.compile(search_pattern)
            except re.error as e:
                return {"error": f"Invalid regex pattern: {e}"}
            
            max_matches = 100
            matches = []
            
            try:
                rg_result = subprocess.run(
                    ['rg', '--line-number', '--no-heading', '--max-count', str(max_matches),
                     search_pattern, search_path] + (['--glob', include] if include else []),
                    capture_output=True, text=True, timeout=30
                )
                if rg_result.returncode == 0:
                    for line in rg_result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split(':', 2)
                            if len(parts) >= 3:
                                matches.append({
                                    "path": parts[0],
                                    "line": int(parts[1]),
                                    "text": parts[2][:200]
                                })
                    return {
                        "success": True,
                        "content": f"Found {len(matches)} matches\n" + "\n".join(
                            f"{m['path']}:{m['line']}: {m['text']}" for m in matches[:50]
                        ),
                        "count": len(matches),
                        "truncated": len(matches) >= max_matches,
                    }
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            
            include_re = None
            if include:
                glob_pattern = include.replace('.', '\\.').replace('*', '.*').replace('?', '.')
                include_re = re.compile(glob_pattern)
            
            for root, dirs, files in os.walk(search_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fname in files:
                    if fname.startswith('.'):
                        continue
                    if include_re and not include_re.match(fname):
                        continue
                    
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                            for line_num, line in enumerate(f, 1):
                                if re.search(search_pattern, line):
                                    matches.append({
                                        "path": fpath,
                                        "line": line_num,
                                        "text": line.strip()[:200]
                                    })
                                    if len(matches) >= max_matches:
                                        break
                    except (PermissionError, OSError):
                        continue
                    if len(matches) >= max_matches:
                        break
            
            if not matches:
                return {"success": True, "content": "No matches found", "count": 0}
            
            output = f"Found {len(matches)} matches\n"
            current_file = ""
            for m in matches[:50]:
                if m["path"] != current_file:
                    if current_file:
                        output += "\n"
                    current_file = m["path"]
                    output += f"{m['path']}:\n"
                output += f"  Line {m['line']}: {m['text']}\n"
            
            if len(matches) > 50:
                output += f"\n... ({len(matches) - 50} more matches)"
            
            return {
                "success": True,
                "content": output,
                "count": len(matches),
                "truncated": len(matches) >= max_matches,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_glob(self, pattern: str, path: str = "") -> Dict:
        """Busca archivos por patrón de nombre"""
        try:
            if not pattern:
                return {"error": "pattern is required"}
            
            search_path = path if path else os.getcwd()
            if not os.path.isabs(search_path):
                search_path = os.path.abspath(search_path)
            
            if not os.path.isdir(search_path):
                return {"error": f"Directory not found: {search_path}"}
            
            search_pattern = os.path.join(search_path, pattern)
            files = glob_module.glob(search_pattern, recursive=True)
            
            files = [f for f in files if os.path.isfile(f) and not os.path.basename(f).startswith('.')]
            files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            
            max_results = 100
            truncated = len(files) > max_results
            if truncated:
                files = files[:max_results]
            
            if not files:
                return {"success": True, "content": "No files found", "count": 0}
            
            output = "\n".join(files)
            if truncated:
                output += f"\n\n(Results truncated. {max_results} of {len(files)}+ files shown.)"
            
            return {
                "success": True,
                "content": output,
                "count": len(files),
                "truncated": truncated,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_git_status(self, path: str = "") -> Dict:
        """Git status - muestra estado del repositorio"""
        try:
            cwd = path if path else os.getcwd()
            if not os.path.isabs(cwd):
                cwd = os.path.abspath(cwd)
            
            result = subprocess.run(
                ["git", "status", "--porcelain", "-b"],
                cwd=cwd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return {"error": f"Not a git repository: {result.stderr.strip()}"}
            
            lines = result.stdout.strip().split('\n')
            branch = lines[0] if lines else "unknown"
            changes = [l for l in lines[1:] if l.strip()] if len(lines) > 1 else []
            
            staged = [l[3:] for l in changes if l[0] in ('A', 'M', 'D', 'R', 'C') and l[1] != ' ']
            unstaged = [l[3:] for l in changes if l[0] == ' ' and l[1] != ' ']
            untracked = [l[3:] for l in changes if l[:2] == '??']
            
            output = f"Branch: {branch}\n"
            if staged:
                output += f"\nStaged ({len(staged)}):\n" + "\n".join(f"  {f}" for f in staged)
            if unstaged:
                output += f"\nModified ({len(unstaged)}):\n" + "\n".join(f"  {f}" for f in unstaged)
            if untracked:
                output += f"\nUntracked ({len(untracked)}):\n" + "\n".join(f"  {f}" for f in untracked)
            if not staged and not unstaged and not untracked:
                output += "\nNothing to commit, working tree clean"
            
            return {
                "success": True,
                "content": output,
                "branch": branch,
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_git_diff(self, path: str = "", staged: bool = False, file_path: str = "") -> Dict:
        """Git diff - muestra cambios no commiteados"""
        try:
            cwd = path if path else os.getcwd()
            if not os.path.isabs(cwd):
                cwd = os.path.abspath(cwd)
            
            cmd = ["git", "diff"]
            if staged:
                cmd.append("--staged")
            if file_path:
                cmd.append("--", file_path)
            
            result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"error": result.stderr.strip()}
            
            diff = result.stdout.strip()
            if not diff:
                return {"success": True, "content": "No changes", "has_changes": False}
            
            lines = diff.split('\n')
            stats = {"additions": 0, "deletions": 0}
            for line in lines:
                if line.startswith('+') and not line.startswith('+++'):
                    stats["additions"] += 1
                elif line.startswith('-') and not line.startswith('---'):
                    stats["deletions"] += 1
            
            max_lines = 200
            if len(lines) > max_lines:
                diff = '\n'.join(lines[:max_lines]) + f"\n\n... ({len(lines) - max_lines} more lines)"
            
            return {
                "success": True,
                "content": diff,
                "has_changes": True,
                "additions": stats["additions"],
                "deletions": stats["deletions"],
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_git_log(self, path: str = "", limit: int = 10) -> Dict:
        """Git log - historial de commits"""
        try:
            cwd = path if path else os.getcwd()
            if not os.path.isabs(cwd):
                cwd = os.path.abspath(cwd)
            
            result = subprocess.run(
                ["git", "log", f"-{limit}", "--oneline", "--decorate"],
                cwd=cwd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return {"error": result.stderr.strip()}
            
            commits = result.stdout.strip().split('\n')
            output = f"Last {len(commits)} commits:\n" + "\n".join(f"  {c}" for c in commits)
            
            return {
                "success": True,
                "content": output,
                "count": len(commits),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_terminal_create(self, name: str = "", cwd: str = "") -> Dict:
        """Crea una terminal persistente usando PersistentShell singleton"""
        try:
            from src.tools.persistent_shell import PersistentShell
            session_id = name or "default"
            work_dir = cwd if cwd else os.getcwd()
            shell = PersistentShell.get_instance(work_dir)
            return {
                "success": True,
                "session_id": session_id,
                "cwd": work_dir,
                "pid": shell._proc.pid if shell._proc else None,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_terminal_send(self, session_id: str, text: str, wait_ms: int = 2000) -> Dict:
        """Envia comando a terminal persistente usando PersistentShell.exec()"""
        try:
            from src.tools.persistent_shell import PersistentShell
            shell = PersistentShell.get_instance()
            timeout_ms = max(wait_ms, 1000)
            stdout, stderr, exit_code, interrupted = await shell.exec(text, timeout_ms)
            output = stdout
            if stderr:
                output += "\n" + stderr
            max_output = 5000
            if len(output) > max_output:
                output = output[:max_output] + f"\n... ({len(output) - max_output} chars truncated)"
            return {
                "success": exit_code == 0 and not interrupted,
                "content": output,
                "session_id": session_id,
                "exit_code": exit_code,
                "running": shell.is_alive,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_terminal_close(self, session_id: str) -> Dict:
        """Cierra terminal persistente"""
        try:
            from src.tools.persistent_shell import PersistentShell
            shell = PersistentShell.get_instance()
            shell.close()
            return {"success": True, "content": f"Terminal '{session_id}' closed"}
        except Exception as e:
            return {"error": str(e)}

    async def _tool_lsp_diagnostics(self, path: str = "", language: str = "") -> Dict:
        """Analiza archivo en busca de errores sintacticos (sin LSP server, usa parser local)"""
        try:
            if not path:
                return {"error": "path is required"}
            
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            
            if not os.path.exists(path):
                return {"error": f"File not found: {path}"}
            
            ext = os.path.splitext(path)[1].lower()
            diagnostics = []
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            if ext == '.py':
                import py_compile
                try:
                    py_compile.compile(path, doraise=True)
                except py_compile.PyCompileError as e:
                    error_msg = str(e)
                    line_match = re.search(r'line (\d+)', error_msg)
                    line_num = int(line_match.group(1)) if line_match else 0
                    diagnostics.append({
                        "severity": "error",
                        "line": line_num,
                        "message": error_msg.split('\n')[0],
                    })
            elif ext in ('.json',):
                import json
                try:
                    with open(path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    diagnostics.append({
                        "severity": "error",
                        "line": e.lineno,
                        "message": str(e.msg),
                    })
            elif ext in ('.yaml', '.yml'):
                try:
                    import yaml
                    with open(path, 'r') as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    line = getattr(e, 'problem_mark', None)
                    line_num = line.line + 1 if line else 0
                    diagnostics.append({
                        "severity": "error",
                        "line": line_num,
                        "message": str(e),
                    })
            
            if diagnostics:
                output = f"Found {len(diagnostics)} issue(s):\n"
                for d in diagnostics:
                    output += f"  Line {d['line']}: [{d['severity']}] {d['message']}\n"
            else:
                output = "No issues found"
            
            return {
                "success": True,
                "content": output,
                "diagnostics": diagnostics,
                "count": len(diagnostics),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_web_fetch(self, url: str, timeout: int = 120) -> Dict:
        """Fetch URL content and convert HTML to Markdown"""
        try:
            from src.tools.web_fetch import web_fetch
            return await web_fetch(url, timeout)
        except Exception as e:
            return {"error": str(e)}

    async def _tool_code_search(self, query: str, path: str = "", include: str = "", limit: int = 20) -> Dict:
        """Search code across files using grep/glob"""
        try:
            from src.tools.code_search import code_search
            return await code_search(query, path, include, limit)
        except Exception as e:
            return {"error": str(e)}

    async def _tool_git_blame(self, path: str, file_path: str) -> Dict:
        """Git blame - muestra quien hizo cada linea"""
        try:
            cwd = path if path else os.getcwd()
            if not os.path.isabs(cwd):
                cwd = os.path.abspath(cwd)
            
            if not file_path:
                return {"error": "file_path is required"}
            
            result = subprocess.run(
                ["git", "blame", "-L", "1,50", file_path],
                cwd=cwd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return {"error": result.stderr.strip()}
            
            lines = result.stdout.strip().split('\n')
            output = f"Git blame (first 50 lines) for {file_path}:\n" + "\n".join(f"  {l}" for l in lines[:50])
            
            return {
                "success": True,
                "content": output,
                "file": file_path,
                "lines": len(lines),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_lsp_symbols(self, path: str) -> Dict:
        """Lista funciones/clases/variables en un archivo Python"""
        try:
            if not path:
                return {"error": "path is required"}
            
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            
            if not os.path.exists(path):
                return {"error": f"File not found: {path}"}
            
            ext = os.path.splitext(path)[1].lower()
            symbols = []
            
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            if ext == '.py':
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if stripped.startswith('def ') or stripped.startswith('async def '):
                        name = stripped.split('(')[0].replace('def ', '').replace('async def ', '')
                        indent = len(line) - len(line.lstrip())
                        symbols.append({"name": name, "type": "function", "line": i, "indent": indent})
                    elif stripped.startswith('class '):
                        name = stripped.split('(')[0].replace('class ', '')
                        symbols.append({"name": name, "type": "class", "line": i})
            elif ext in ('.js', '.ts'):
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if re.match(r'(export\s+)?(async\s+)?function\s+', stripped):
                        name = re.search(r'function\s+(\w+)', stripped)
                        if name:
                            symbols.append({"name": name.group(1), "type": "function", "line": i})
                    elif re.match(r'(export\s+)?class\s+', stripped):
                        name = re.search(r'class\s+(\w+)', stripped)
                        if name:
                            symbols.append({"name": name.group(1), "type": "class", "line": i})
            
            if symbols:
                output = f"Found {len(symbols)} symbols in {os.path.basename(path)}:\n"
                for s in symbols:
                    indent = "  " * (s.get("indent", 0) // 4) if s.get("indent") else ""
                    output += f"  Line {s['line']}: {s['type']} {s['name']}\n"
            else:
                output = "No symbols found"
            
            return {
                "success": True,
                "content": output,
                "symbols": symbols,
                "count": len(symbols),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_workspace_folders(self) -> Dict:
        """Lista carpetas del workspace actual"""
        try:
            cwd = os.getcwd()
            entries = []
            for entry in os.listdir(cwd):
                full_path = os.path.join(cwd, entry)
                if os.path.isdir(full_path) and not entry.startswith('.'):
                    file_count = sum(1 for _ in os.walk(full_path))
                    entries.append({"name": entry, "path": full_path, "type": "folder", "file_count": file_count})
            
            output = f"Workspace folders in {cwd}:\n"
            for e in entries:
                output += f"  📁 {e['name']} ({e['file_count']} files)\n"
            
            return {
                "success": True,
                "content": output,
                "folders": entries,
                "count": len(entries),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_find_files(self, pattern: str, path: str = "", use_ignore: bool = True) -> Dict:
        """Busca archivos respetando .gitignore"""
        try:
            search_path = path if path else os.getcwd()
            if not os.path.isabs(search_path):
                search_path = os.path.abspath(search_path)
            
            if not os.path.isdir(search_path):
                return {"error": f"Directory not found: {search_path}"}
            
            import fnmatch
            ignore_patterns = []
            
            if use_ignore:
                gitignore = os.path.join(search_path, '.gitignore')
                if os.path.exists(gitignore):
                    with open(gitignore, 'r') as f:
                        ignore_patterns = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            
            def should_ignore(p):
                for pat in ignore_patterns:
                    if fnmatch.fnmatch(os.path.basename(p), pat):
                        return True
                    if fnmatch.fnmatch(p, pat):
                        return True
                return False
            
            results = []
            for root, dirs, files in os.walk(search_path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and not should_ignore(os.path.join(root, d))]
                for f in files:
                    full = os.path.join(root, f)
                    if not should_ignore(full) and fnmatch.fnmatch(f, pattern):
                        results.append(full)
            
            results.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            
            max_results = 100
            truncated = len(results) > max_results
            if truncated:
                results = results[:max_results]
            
            output = "\n".join(results) if results else "No files found"
            if truncated:
                output += f"\n\n({max_results} of {len(results)}+ files shown)"
            
            return {
                "success": True,
                "content": output,
                "count": len(results),
                "truncated": truncated,
            }
        except Exception as e:
            return {"error": str(e)}

    async def _tool_git_commit(self, path: str, message: str) -> Dict:
        """Git commit - crea un commit con mensaje"""
        try:
            cwd = path if path else os.getcwd()
            if not os.path.isabs(cwd):
                cwd = os.path.abspath(cwd)
            
            # Add all changes
            subprocess.run(["git", "add", "."], cwd=cwd, capture_output=True, timeout=30)
            
            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=cwd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                if "nothing to commit" in result.stdout.lower():
                    return {"success": True, "content": "Nothing to commit, working tree clean", "committed": False}
                return {"error": result.stderr.strip()}
            
            return {
                "success": True,
                "content": result.stdout.strip(),
                "committed": True,
            }
        except Exception as e:
            return {"error": str(e)}

    async def execute_tool_call(self, tool_name: str, params: Dict) -> Dict:
        """Ejecuta una llamada a herramienta builtin"""
        try:
            if tool_name == "read_file":
                return self.workspace.read_file(
                    params.get("path", ""),
                    params.get("offset", 1),
                    params.get("limit", 2000)
                )
            elif tool_name == "view_file":
                return await self._tool_view_file(
                    params.get("path", ""),
                    params.get("offset", 0),
                    params.get("limit", 2000)
                )
            elif tool_name == "write_file":
                return self.workspace.write_file(
                    params.get("path", ""),
                    params.get("content", ""),
                    params.get("mkdirp", True)
                )
            elif tool_name == "edit_file":
                return await self._tool_edit_file(
                    params.get("path", ""),
                    params.get("old_string", ""),
                    params.get("new_string", "")
                )
            elif tool_name == "patch_files":
                return await self._tool_patch_files(
                    params.get("patch_text", "")
                )
            elif tool_name == "list_dir":
                return self.workspace.list_dir(
                    params.get("path", ""),
                    params.get("recursive", False)
                )
            elif tool_name == "grep_content":
                return await self._tool_grep(
                    params.get("pattern", ""),
                    params.get("path", ""),
                    params.get("include", ""),
                    params.get("literal", False)
                )
            elif tool_name == "glob_files":
                return await self._tool_glob(
                    params.get("pattern", ""),
                    params.get("path", "")
                )
            elif tool_name == "execute_command":
                return await self.executor.execute_command(
                    params.get("command", ""),
                    params.get("cwd"),
                    params.get("timeout", 60)
                )
            elif tool_name == "parse_file":
                from src.tools.builtin import ParseTools
                return ParseTools().parse_file(params.get("path", ""))
            elif tool_name == "git_status":
                return await self._tool_git_status(params.get("path", ""))
            elif tool_name == "git_diff":
                return await self._tool_git_diff(
                    params.get("path", ""),
                    params.get("staged", False),
                    params.get("file", "")
                )
            elif tool_name == "git_log":
                return await self._tool_git_log(
                    params.get("path", ""),
                    params.get("limit", 10)
                )
            elif tool_name == "terminal_create":
                return await self._tool_terminal_create(
                    params.get("name", ""),
                    params.get("cwd", "")
                )
            elif tool_name == "terminal_send":
                return await self._tool_terminal_send(
                    params.get("session_id", ""),
                    params.get("text", ""),
                    params.get("wait_ms", 2000)
                )
            elif tool_name == "terminal_close":
                return await self._tool_terminal_close(
                    params.get("session_id", "")
                )
            elif tool_name == "lsp_diagnostics":
                return await self._tool_lsp_diagnostics(
                    params.get("path", ""),
                    params.get("language", "")
                )
            elif tool_name == "web_fetch":
                return await self._tool_web_fetch(
                    params.get("url", ""),
                    params.get("timeout", 120)
                )
            elif tool_name == "code_search":
                return await self._tool_code_search(
                    params.get("query", ""),
                    params.get("path", ""),
                    params.get("include", ""),
                    params.get("limit", 20)
                )
            elif tool_name == "git_blame":
                return await self._tool_git_blame(
                    params.get("path", ""),
                    params.get("file", "")
                )
            elif tool_name == "lsp_symbols":
                return await self._tool_lsp_symbols(
                    params.get("path", "")
                )
            elif tool_name == "workspace_folders":
                return await self._tool_workspace_folders()
            elif tool_name == "find_files":
                return await self._tool_find_files(
                    params.get("pattern", ""),
                    params.get("path", ""),
                    params.get("use_ignore", True)
                )
            elif tool_name == "git_commit":
                return await self._tool_git_commit(
                    params.get("path", ""),
                    params.get("message", "")
                )
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": str(e)}

    def get_tool_definitions(self) -> List[Dict]:
        """Retorna definiciones de herramientas para el modelo"""
        return [
            {
                "name": "view_file",
                "description": "Lee el contenido de un archivo con números de línea y paginación. Usa offset para leer desde una línea específica.",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta absoluta del archivo"},
                    "offset": {"type": "integer", "description": "Línea inicial (0-based, default: 0)"},
                    "limit": {"type": "integer", "description": "Número de líneas (default: 2000)"}
                }
            },
            {
                "name": "edit_file",
                "description": "Reemplaza texto en un archivo. old_string debe ser único y coincidir exactamente con el contenido del archivo incluyendo indentación.",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta absoluta del archivo"},
                    "old_string": {"type": "string", "description": "Texto a reemplazar (debe ser único en el archivo)"},
                    "new_string": {"type": "string", "description": "Nuevo texto"}
                }
            },
            {
                "name": "patch_files",
                "description": "Aplica un patch a múltiples archivos en una operación coordinada. Formato: *** Begin Patch\\n*** Update File: /path\\n@@ context\\n-remove\\n+add\\n*** End Patch",
                "parameters": {
                    "patch_text": {"type": "string", "description": "Texto completo del patch"}
                }
            },
            {
                "name": "grep_content",
                "description": "Busca contenido en archivos usando regex. Retorna archivos con coincidencias y líneas matching.",
                "parameters": {
                    "pattern": {"type": "string", "description": "Patrón regex a buscar"},
                    "path": {"type": "string", "description": "Directorio donde buscar (default: cwd)"},
                    "include": {"type": "string", "description": "Patrón de archivo para incluir (ej: '*.py')"},
                    "literal": {"type": "boolean", "description": "Tratar pattern como texto literal (default: false)"}
                }
            },
            {
                "name": "glob_files",
                "description": "Busca archivos por patrón de nombre (glob). No busca contenido, solo nombres.",
                "parameters": {
                    "pattern": {"type": "string", "description": "Patrón glob (ej: '**/*.py')"},
                    "path": {"type": "string", "description": "Directorio donde buscar (default: cwd)"}
                }
            },
            {
                "name": "read_file",
                "description": "Lee el contenido de un archivo con paginación",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del archivo relativa al workspace"},
                    "offset": {"type": "integer", "description": "Línea inicial (default: 1)"},
                    "limit": {"type": "integer", "description": "Número de líneas (default: 2000)"}
                }
            },
            {
                "name": "write_file",
                "description": "Escribe contenido a un archivo",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del archivo"},
                    "content": {"type": "string", "description": "Contenido a escribir"},
                    "mkdirp": {"type": "boolean", "description": "Crear directorios padres (default: true)"}
                }
            },
            {
                "name": "list_dir",
                "description": "Lista contenido de un directorio",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del directorio (vacío = root)"},
                    "recursive": {"type": "boolean", "description": "Listado recursivo (default: false)"}
                }
            },
            {
                "name": "execute_command",
                "description": "Ejecuta un comando en la terminal",
                "parameters": {
                    "command": {"type": "string", "description": "Comando a ejecutar"},
                    "cwd": {"type": "string", "description": "Directorio de trabajo"},
                    "timeout": {"type": "integer", "description": "Timeout en segundos (default: 60)"}
                }
            },
            {
                "name": "parse_file",
                "description": "Parsea un archivo según su extensión (JSON, código, etc.)",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del archivo"}
                }
            },
            {
                "name": "git_status",
                "description": "Muestra el estado del repositorio git (archivos modificados, staged, untracked)",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del repositorio (default: cwd)"}
                }
            },
            {
                "name": "git_diff",
                "description": "Muestra los cambios no commiteados. staged=true para ver cambios staged.",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del repositorio (default: cwd)"},
                    "staged": {"type": "boolean", "description": "Ver cambios staged (default: false)"},
                    "file": {"type": "string", "description": "Archivo específico para diff"}
                }
            },
            {
                "name": "git_log",
                "description": "Historial de commits del repositorio",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del repositorio (default: cwd)"},
                    "limit": {"type": "integer", "description": "Número de commits (default: 10)"}
                }
            },
            {
                "name": "terminal_create",
                "description": "Crea una terminal persistente con session ID para enviar comandos secuencialmente",
                "parameters": {
                    "name": {"type": "string", "description": "Nombre de la sesión (auto-generado si vacío)"},
                    "cwd": {"type": "string", "description": "Directorio de trabajo"}
                }
            },
            {
                "name": "terminal_send",
                "description": "Envia texto a una terminal persistente y retorna output",
                "parameters": {
                    "session_id": {"type": "string", "description": "ID de la sesión de terminal"},
                    "text": {"type": "string", "description": "Comando o texto a enviar"},
                    "wait_ms": {"type": "integer", "description": "Milisegundos a esperar antes de leer output (default: 2000)"}
                }
            },
            {
                "name": "terminal_close",
                "description": "Cierra una terminal persistente",
                "parameters": {
                    "session_id": {"type": "string", "description": "ID de la sesión de terminal"}
                }
            },
            {
                "name": "lsp_diagnostics",
                "description": "Analiza un archivo en busca de errores sintácticos (Python, JSON, YAML)",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del archivo a analizar"},
                    "language": {"type": "string", "description": "Lenguaje (auto-detectado por extensión)"}
                }
            },
            {
                "name": "web_fetch",
                "description": "Obtiene contenido de una URL y convierte HTML a Markdown",
                "parameters": {
                    "url": {"type": "string", "description": "URL a obtener"},
                    "timeout": {"type": "integer", "description": "Timeout en segundos (default: 120)"}
                }
            },
            {
                "name": "code_search",
                "description": "Busca código en archivos usando regex. Soporta filtros por patrón de archivo.",
                "parameters": {
                    "query": {"type": "string", "description": "Patrón regex a buscar"},
                    "path": {"type": "string", "description": "Directorio donde buscar (default: cwd)"},
                    "include": {"type": "string", "description": "Patrón de archivo para incluir (ej: '*.py')"},
                    "limit": {"type": "integer", "description": "Máximo resultados (default: 20)"}
                }
            },
            {
                "name": "git_blame",
                "description": "Muestra quien hizo cada linea de un archivo (git blame)",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del repositorio (default: cwd)"},
                    "file": {"type": "string", "description": "Archivo para blame"}
                }
            },
            {
                "name": "lsp_symbols",
                "description": "Lista funciones, clases y variables en un archivo (Python, JS, TS)",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del archivo"}
                }
            },
            {
                "name": "workspace_folders",
                "description": "Lista carpetas del workspace actual con conteo de archivos",
                "parameters": {}
            },
            {
                "name": "find_files",
                "description": "Busca archivos por patron respetando .gitignore",
                "parameters": {
                    "pattern": {"type": "string", "description": "Patron glob (ej: '*.py')"},
                    "path": {"type": "string", "description": "Directorio donde buscar (default: cwd)"},
                    "use_ignore": {"type": "boolean", "description": "Respetar .gitignore (default: true)"}
                }
            },
            {
                "name": "git_commit",
                "description": "Crea un commit git con mensaje",
                "parameters": {
                    "path": {"type": "string", "description": "Ruta del repositorio (default: cwd)"},
                    "message": {"type": "string", "description": "Mensaje del commit"}
                }
            }
        ]
