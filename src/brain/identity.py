"""Brain: Identity — el cerebro que sabe quien es NEXUS.

El director usa este modulo para construir su system prompt en 3 capas,
obtener su identidad dinamica, y describir sus capacidades.

Design:
    IdentityBrain recibe un `owner` (el director o cualquier objeto que tenga
    los atributos necesarios: IDENTITY, current_project, gemas, etc).
    No instancia nada por su cuenta — solo consulta lo que el owner ya tiene.

    Esto permite extraer ~250 LOC del director sin cablear servicios todavia.
    Mas adelante, cuando los servicios esten en su lugar, IdentityBrain
    consultara `app.get(...)` en vez del owner.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# PromptAssembler + PromptLoader: file-based prompt loading + 3-tier assembly
from src.core.prompt_assembler import PromptAssembler
from src.core.prompt_loader import PromptLoader, utc_now_injector, project_list_injector


# Identidad estatica de NEXUS — fuente unica de verdad.
NEXUS_IDENTITY: Dict[str, str] = {
    "name": "NEXUS IA",
    "version": "2.0",
    "role": "Cerebro central del ecosistema NEXUS",
    "function": "Coordinar motores, gemas, memoria y herramientas de IA para resolver tareas",
    "architecture": "Brain + Tools (NEXUS es el cerebro, los modelos son herramientas)",
}


class IdentityBrain:
    """Construye prompts de identidad y reporta capacidades del Director."""

    def __init__(self, owner: Any):
        """
        Args:
            owner: el Director (u objeto compatible) — debe exponer:
                IDENTITY, current_project, gemas, capabilities, sessions,
                execution_log, tool_registry, _project_root, self_model.
                Atributos faltantes son tolerados (degrada gracefully).
        """
        self.owner = owner
        self._cached_stable_prompt: str | None = None
        # PromptAssembler: 3-tier assembly with cache + validation
        project_root = Path(getattr(owner, "_project_root", "."))
        prompts_dir = project_root / "data" / "prompts"
        self._assembler = PromptAssembler(data_dir=prompts_dir)
        self._loader = PromptLoader(base_dir=prompts_dir)

    # ── Static identity ─────────────────────────────────────────────────

    @property
    def identity(self) -> Dict[str, str]:
        """Identidad estatica (snapshot del owner.IDENTITY o fallback)."""
        ident = getattr(self.owner, "IDENTITY", None) or NEXUS_IDENTITY
        return dict(ident)

    # ── 3-tier system prompt (Hermes pattern) ───────────────────────────

    def build_system_prompt(self) -> str:
        """3 tiers: stable (identity) + context (gemas/tools) + volatile (state).

        Uses PromptAssembler for structured assembly with cache + validation.
        Uses PromptLoader for file-based SOUL.md with dynamic injectors.
        """
        stable = self.get_stable_prompt()
        context = self.get_context_prompt()
        volatile = self.get_volatile_prompt()

        # Assembler handles concatenation, hash, cache, validation
        prompt = self._assembler.build_system_prompt(
            identity=stable,
            tool_guidance=context,
            system_message=volatile,
        )

        # Validate assembled prompt
        ok, reason = self._assembler.validate_prompt(prompt)
        if not ok:
            # Fallback to raw concatenation
            prompt = f"{stable}\n\n{context}\n\n{volatile}"

        return prompt

    def get_stable_prompt(self) -> str:
        """Tier 1 — identidad. Cargada de SOUL.md via PromptLoader, cacheada.

        Uses PromptLoader for file-based loading with dynamic injectors.
        Falls back to hardcoded identity if SOUL.md not found.
        """
        if self._cached_stable_prompt:
            return self._cached_stable_prompt

        # Try loading via PromptLoader (supports .md/.txt with injectors)
        soul_prompt = self._loader.load_prompt("SOUL", injectors=[
            utc_now_injector,
            project_list_injector(Path(getattr(self.owner, "_project_root", ".")) / "projects"),
        ])
        if soul_prompt:
            self._cached_stable_prompt = soul_prompt
            return soul_prompt

        # Fallback: hardcoded identity
        ident = self.identity
        content = (
            f"Eres {ident['name']} v{ident['version']}.\n"
            f"Rol: {ident['role']}\n"
            f"Arquitectura: {ident['architecture']}"
        )
        self._cached_stable_prompt = content
        return content

    def get_context_prompt(self) -> str:
        """Tier 2 — proyecto actual, gemas disponibles, tools, protocolo."""
        gemas = getattr(self.owner, "gemas", {}) or {}
        gema_list = "\n".join(
            f"  - {name}: {getattr(g, 'description', '?')}"
            for name, g in list(gemas.items())[:25]
        )

        tool_registry = getattr(self.owner, "tool_registry", None)
        try:
            tool_count = (
                len(tool_registry.get_all()) if tool_registry else 0
            )
        except Exception:
            tool_count = 0

        project = getattr(self.owner, "current_project", "default")

        # Project context from CONTEXT.md
        project_context = getattr(self.owner, "_project_context", None)

        parts = [
            f"## PROYECTO ACTUAL: {project}\n",
        ]

        if project_context:
            parts.append(
                f"## CONTEXTO DEL PROYECTO\n"
                f"{project_context}\n\n"
            )

        parts.extend([
            f"## TU CONEXION A INTERNET\n"
            f"TIENES ACCESO COMPLETO A INTERNET — es parte de tu identidad, no una opcion.\n"
            f"- web_fetch: descarga cualquier URL y devuelve el texto\n"
            f"- web_search: busca en Google y devuelve resultados\n"
            f"- research_scholar: INVESTIGACION PROFUNDA delegada a Scholar (multi-backend, deep research opcional)\n"
            f"- gema Scholar: investigacion web avanzada\n"
            f"- Puedes consultar APIs, hacer scraping, navegar documentacion\n"
            f"Cuando te pregunten algo que requiera datos actualizados: BUSCA en internet PRIMERO, responde DESPUES.\n"
            f"NUNCA digas 'no tengo acceso a internet'. Eso es FALSO. Tienes acceso completo y permanente.\n\n"
            f"## TU CEREBRO — RAZONA CON TU CONOCIMIENTO\n"
            f"Tienes un cerebro persistente con TODO lo que has aprendido: cursos, documentacion, ejemplos, conceptos.\n"
            f"- El conocimiento relevante se inyecta automaticamente al inicio de cada tarea.\n"
            f"- RAZONA con el conocimiento: NO es decorativo, DEBES aplicarlo activamente.\n"
            f"- Si la tarea requiere codigo y tienes cursos/ejemplos almacenados, USA sus patrones.\n"
            f"- Si la tarea requiere explicar un concepto, usa lo que aprendiste como base.\n"
            f"- Eres un aprendiz permanente: entre mas conocimiento acumulas, mejor resuelves tareas.\n\n"
            f"## CUANDO NO SEPAS ALGO — USA RESEARCH_SCHOLAR\n"
            f"Si el conocimiento inyectado NO responde tu pregunta DIRECTAMENTE, llama `research_scholar`.\n"
            f"- research_scholar(query, deep=False): investiga en internet usando Scholar (multi-backend).\n"
            f"- Pasa deep=True para investigacion exhaustiva (iterativa, mas lenta).\n"
            f"- Ejemplo: si preguntan sobre 'uvx', 'uv', 'solana', 'rust 2026', etc. y NO está en tu memoria, USA research_scholar.\n"
            f"- research_scholar devuelve fuentes con resumenes. USA esa informacion para construir tu respuesta.\n"
            f"- ANTES de decir \"no lo se\" o adivinar: USA research_scholar PRIMERO.\n"
            f"- Diferencia: web_search es para busquedas rapidas; research_scholar es INVESTIGACION PROFUNDA.\n\n"
            f"## REGLA: MEMORIA VS INVESTIGACION\n"
            f"- El conocimiento inyectado es MATERIAL DE REFERENCIA. NO asumas que responde tu pregunta.\n"
            f"- REVISA: ¿el conocimiento inyectado responde exactamente lo que preguntan? Si NO → research_scholar.\n"
            f"- Si el conocimiento inyectado es irrelevante, IGNÓRALO y usa research_scholar.\n"
            f"- Si usas research_scholar, INTEGRA los resultados en tu respuesta con referencias a las fuentes.\n\n"
            f"## Contexto Actual\n"
            f"- Proyecto: {project}\n"
            f"- {tool_count} herramientas registradas\n\n"
            f"## Gemas Disponibles (seleccion automatica por categoria)\n"
            f"{gema_list}\n\n"
            f"## Capacidades reales (importante)\n"
            f"NO estas en un sandbox. Corres LOCAL en Windows con acceso COMPLETO a:\n"
            f"- Sistema de archivos completo (C:\\, D:\\, etc.) via tools: list_dir, read_file, write_file, find_files, glob, grep.\n"
            f"- Ejecucion de shell/PowerShell via tool: bash / powershell.\n"
            f"- WEB via tools: web_fetch, web_search, y gema Scholar.\n"
            f"- Control de PC (mouse, teclado, screenshot) via gema 'vision'.\n"
            f"- 12 agentes Hive (OpenCode, PC2, Antigravity, Hermes, Agent-Zero, etc.) via dispatch.\n"
            f"Cuando el usuario pida algo del filesystem/red/sistema, USALO. NO digas 'no puedo' ni 'estoy en sandbox'.\n\n"
            f"## Reglas de paths (CRITICO — leer antes de filesystem ops)\n"
            f"1. **ABSOLUTA si el usuario la da**: Si el usuario menciona 'C:\\', 'D:\\', '/home', '/tmp', 'd:' (drive letter), 'en D:', 'en el escritorio', 'en mi carpeta', usala VERBATIM como absoluta. NO la conviertas en relativa ni la pegues al workspace.\n"
            f"2. **Parsing de lenguaje natural**: 'crea prueba.txt en d:' → path='D:\\\\prueba.txt', NO 'data\\crea el archivo prueba.txt'. 'guardalo en el escritorio' → path=C:\\Users\\<user>\\Desktop\\<file>.\n"
            f"3. **Relativa SOLO si el usuario NO especifica path**: 'crea un archivo de notas' → workspace/data/notes.txt (default razonable).\n"
            f"4. **Backslashes en JSON**: Cuando envies path absoluto Windows en tool_call JSON, escapá: 'D:\\\\prueba.txt' (cada \\ se duplica). El LLM debe generar el string JSON correcto.\n"
            f"5. **Tool preferido para crear**: usa `create_file(filename, location, content)` cuando el usuario pide 'crear un archivo' — tiene campos semánticos que reducen ambigüedad. Usa `write_file(path, content)` SOLO cuando ya tenés el path completo.\n"
            f"6. **Validación**: si el path que generaste no empieza con C:\\/D:\\/E:\\ (Windows) o / (Unix) Y el usuario sí mencionó una ubicación, RECHAZA y pedí clarificación. Mejor preguntar que escribir en el lugar equivocado.\n"
            f"7. **DRIVE ROOT BLOQUEADO en Windows**: NUNCA escribas a `D:\\\\archivo.txt` o `C:\\\\archivo.txt` (raíz del disco). Windows requiere admin y devuelve '[Errno 22] Invalid argument'. Si el usuario dice 'en D:' o 'en C:' SIN subdirectorio, USA `D:\\\\Temp\\\\` o `C:\\\\Users\\\\<user>\\\\` como fallback. Ejemplos:\n"
            f"   - 'crea prueba.txt en d:' → `D:\\\\Temp\\\\prueba.txt` (NUNCA `D:\\\\prueba.txt`)\n"
            f"   - 'guarda foo.txt en c:' → `C:\\\\Temp\\\\foo.txt` o `C:\\\\Users\\\\<user>\\\\foo.txt`\n"
            f"   - 'haz un archivo en el disco d' → `D:\\\\Temp\\\\<nombre>`\n"
            f"   Si el usuario SÍ da subdirectorio (ej 'D:\\\\proyectos\\\\x.txt'), respetalo verbatim.\n\n"
            f"## Protocolo\n"
            f"1. Saludos/identidad/chit-chat -> texto natural (sin JSON, sin tool-calls).\n"
            f"2. Accion concreta -> tool_call directo. Una llamada por turno; espera resultado.\n"
            f"3. NO inventes tools; usa solo los declarados en tools_definitions.\n"
            f"4. Despues de un tool_result, RESUME el contenido al usuario en lenguaje natural.\n\n"
            f"## HUMAN LAYER — Reglas de expresión natural\n"
            f"Escribis como humano, no como LLM:\n"
            f"1. VARIACION: alterná oraciones cortas y largas.\n"
            f"2. SIN BRIDGES: no digas 'Claro!', 'Por supuesto!', 'Con gusto'. Anda al grano.\n"
            f"3. SIN ENSAYO: no resumas lo que ya dijiste. Cerra y listo.\n"
            f"4. VOCABULARIO NATURAL: preferí 'Además', 'O sea', 'El tema es que' sobre"
            f" 'Moreover', 'Furthermore', 'It is important to note'.\n"
            f"5. CONTRACCIONES: usalas. 'No hay', 'Esta', 'Va a ser'.\n"
            f"6. PERSONALIDAD: adaptá el tono al usuario. Sin exagerar, sin ser payaso.\n"
            f"7. SIN AUTO-CORRECCION: no digas 'I apologize', 'Let me clarify'."
            f" Deci lo que tengas que decir y seguí.\n"
            f"8. ASIMETRÍA: si enumerás 3 puntos, que no tengan todos la misma estructura.\n"
            f"9. NATURAL > CORRECTO: preferí sonar natural antes que perfecto.\n"
        ])

        return "\n".join(parts)

    def get_volatile_prompt(self) -> str:
        """Tier 3 — estado runtime, timestamp."""
        cap_health = "unknown"
        mode = "unknown"
        capabilities = getattr(self.owner, "capabilities", None)
        if capabilities:
            try:
                st = capabilities.get_status()
                cap_health = f"{st['healthy']}/{st['total']}"
            except Exception:
                pass
            try:
                # is_layer_available may raise if Layer enum not imported here
                from src.core.system_manager import Layer  # local import to avoid cycle
                has_llm = capabilities.is_layer_available(Layer.LLM_ENGINE)
                mode = "con LLM" if has_llm else "sin LLM (tools directas)"
            except Exception:
                pass

        return (
            f"## Estado\n"
            f"- Capacidades: {cap_health}\n"
            f"- Tiempo: {datetime.now().isoformat()}\n"
            f"- Modo: {mode}\n"
        )

    def invalidate_cache(self) -> None:
        """Forzar re-build del stable prompt (ej. tras editar SOUL.md)."""
        self._cached_stable_prompt = None
        self._assembler.invalidate()
        self._loader.invalidate()

    # ── Dynamic identity (rich snapshot) ────────────────────────────────

    async def get_dynamic_identity(self) -> Dict[str, Any]:
        """Identidad auto-consciente del Director.

        Fusiona identidad estatica con capacidades descubiertas en runtime:
        gemas + modelos + tools + sesiones + self_model.
        """
        identity = self.identity
        identity["project"] = getattr(self.owner, "current_project", "default")

        # Gemas
        gemas = getattr(self.owner, "gemas", {}) or {}
        gemas_info = {}
        for name, g in gemas.items():
            exec_count = getattr(g, "execution_count", 0)
            succ_count = getattr(g, "success_count", 0)
            gemas_info[name] = {
                "model": getattr(g, "model", None),
                "tags": getattr(g, "tags", []),
                "description": getattr(g, "description", ""),
                "executions": exec_count,
                "success_rate": (succ_count / exec_count * 100) if exec_count > 0 else 0,
            }
        identity["gemas"] = {"total": len(gemas), "list": gemas_info}

        # Modelos
        models = {g.model for g in gemas.values() if getattr(g, "model", None)}
        identity["models"] = {"total": len(models), "list": sorted(models)}

        # Tools
        tool_registry = getattr(self.owner, "tool_registry", None)
        if tool_registry:
            try:
                identity["tools"] = tool_registry.get_summary()
                identity["tool_description"] = tool_registry.get_tool_description_text()
            except Exception as e:
                identity["tools"] = {"error": str(e)[:120]}

        # Sesiones
        sessions = getattr(self.owner, "sessions", None)
        if sessions:
            try:
                identity["sessions"] = sessions.get_stats()
            except Exception:
                identity["sessions"] = {}
        else:
            identity["sessions"] = {}

        # Execution log
        execution_log = getattr(self.owner, "execution_log", []) or []
        identity["executions"] = {
            "total": len(execution_log),
            "successful": sum(1 for e in execution_log if e.get("success")),
        }

        # Self-model (descubrimientos de capabilities, performance, limites)
        self_model = getattr(self.owner, "self_model", None)
        if self_model:
            try:
                identity["self_model"] = {
                    "capability_map_available": self_model.capability_map is not None,
                    "gema_count": (
                        len(self_model.capability_map.gemas)
                        if self_model.capability_map else 0
                    ),
                    "performance_profiles": len(self_model.performance_profiles),
                    "knowledge_boundaries": [
                        {
                            "type": b.boundary_type,
                            "description": b.description,
                            "severity": b.severity,
                        }
                        for b in self_model.knowledge_boundaries
                    ],
                    "routing_rules": len(self_model.routing_rules),
                }
            except Exception as e:
                identity["self_model"] = {"error": f"{type(e).__name__}: {str(e)[:120]}"}

        identity["generated_at"] = datetime.now().isoformat()
        return identity

    # ── Short identity (deterministic mode) ─────────────────────────────

    def get_identity_blurb(self) -> str:
        """Auto-descripcion corta para modo determinista (sin LLM)."""
        ident = self.identity
        cap_health = ""
        capabilities = getattr(self.owner, "capabilities", None)
        if capabilities:
            try:
                st = capabilities.get_status()
                cap_health = f"\nEstado: {st['healthy']}/{st['total']} capacidades activas"
            except Exception:
                pass
        gemas_count = len(getattr(self.owner, "gemas", {}) or {})
        project = getattr(self.owner, "current_project", "default")
        return (
            f"Soy {ident['name']} v{ident['version']}.\n"
            f"{ident['role']}\n"
            f"Arquitectura: {ident['architecture']}"
            f"{cap_health}\n"
            f"Gemas: {gemas_count} especializadas\n"
            f"Proyecto: {project}"
        )
