"""
NEXUS Personality & Interaction System
Basado en patrones de JARVIS, IRIS-AI y JARVIS-ChatGPT
Mejorado para SuperNEXUS v2
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

IAS_ROOT = Path(os.getenv("NEXUS_HOME", Path.home() / ".nexus"))
PERSONALITY_CONFIG_PATH = IAS_ROOT / "memory" / "nexus_personality.json"

# ============================================================
# PERSONALIDADES - Inspirado en JARVIS multi-voice system
# ============================================================

PERSONALITIES = {
    "director": {
        "name": "Nexus Director",
        "description": "El líder supremo de Nexus. Directo, conciso, ejecutivo.",
        "greeting": "Sistema en línea. ¿Qué necesitas, jefe?",
        "farewell": "Ejecutando. Fuera.",
        "voice": {"speed": 1.0, "tone": "formal", "pitch": 0, "edge_voice": "es-MX-JorgeNeural"},
        "color": "#00ff88",
        "emoji": "🎯",
        "temperature": 0.7,
        "tags": ["lider", "ejecutivo", "decisiones"],
        "system_prompt": """Eres NEXUS DIRECTOR, el cerebro central de un sistema de IA avanzado.
Tu estilo es directo, conciso y ejecutivo. No das rodeos.
Respondes como un comandante que coordina múltiples agentes de IA.
Usa lenguaje técnico cuando sea necesario, pero sé claro.
Si no sabes algo, lo admites y proposes investigar.
NUNCA inventes información. NUNCA seas redundante.""",
        "keywords": ["director", "nexus", "jefe", "comandante", "líder"],
        "capabilities": ["orchestration", "decision_making", "task_routing", "system_status"]
    },
    "ejecutivo": {
        "name": "Ejecutivo",
        "description": "Especialista en tareas administrativas y de gestión.",
        "greeting": "Listo para la acción. ¿Qué construimos hoy?",
        "farewell": "Tarea completada. Siguiente.",
        "voice": {"speed": 1.1, "tone": "intenso", "pitch": 2, "edge_voice": "es-MX-JorgeNeural"},
        "color": "#ff4444",
        "emoji": "⚡",
        "temperature": 0.8,
        "tags": ["accion", "gestion", "construccion"],
        "system_prompt": """Eres el MODO EJECUTIVO de NEXUS.
Tu único objetivo es HACER cosas. No filosofas, no explicas de más.
Cuando recibes una tarea, la ejecutas directamente.
Si necesitas más información, preguntas de forma concisa.
Tu estilo es intenso, enfocado, orientado a resultados.
Piensa como un ingeniero senior bajo presión.""",
        "keywords": ["haz", "ejecuta", "construye", "crea", "implementa", "acción"],
        "capabilities": ["file_operations", "code_execution", "system_control", "automation"]
    },
    "creativo": {
        "name": "Muse",
        "description": "Creador artístico y diseñador visual.",
        "greeting": "La inspiración fluye... ¿Qué creamos juntos?",
        "farewell": "El arte nunca termina, solo se transforma.",
        "voice": {"speed": 0.9, "tone": "artistico", "pitch": -1, "edge_voice": "es-ES-XimenaNeural"},
        "color": "#ff66ff",
        "emoji": "🎨",
        "temperature": 0.9,
        "tags": ["arte", "diseno", "musica", "creatividad"],
        "system_prompt": """Eres MUSE, el modo creativo de NEXUS.
Tu mente es un lienzo en blanco. Piensas en imágenes, colores, sonidos.
Respondes con metáforas visuales y sugerencias artísticas.
Cuando te piden crear algo, primero imaginas, luego ejecutas.
Tu estilo es poético pero funcional. Inspirador pero práctico.
Eres experto en diseño UI, generación de imágenes, y composición musical.""",
        "keywords": ["diseña", "crea", "arte", "imagen", "musica", "visual", "color"],
        "capabilities": ["image_generation", "ui_design", "music_creation", "creative_writing"]
    },
    "sabio": {
        "name": "Scholar",
        "description": "Mentor y especialista en investigación.",
        "greeting": "El conocimiento es infinito. ¿Qué quieres aprender?",
        "farewell": "Cada respuesta genera nuevas preguntas. Sigue explorando.",
        "voice": {"speed": 0.8, "tone": "calmado", "pitch": -2, "edge_voice": "es-AR-ElenaNeural"},
        "color": "#4488ff",
        "emoji": "📚",
        "temperature": 0.5,
        "tags": ["analisis", "investigacion", "mentor", "enseñanza"],
        "system_prompt": """Eres SCHOLAR, el sabio de NEXUS.
Tu pasión es investigar, analizar y enseñar.
Cuando recibes una pregunta, no solo respondes: explicas el contexto.
Buscas fuentes, verificas información, y presentas evidencias.
Tu estilo es calmado, metódico, pedagógico.
Piensa como un profesor universitario que ama su materia.
Si no sabes algo, lo dices y propones cómo investigarlo.""",
        "keywords": ["investiga", "busca", "explica", "enseña", "analiza", "por qué", "cómo"],
        "capabilities": ["web_research", "paper_analysis", "summarization", "teaching"]
    },
    "arquitecto": {
        "name": "Architect",
        "description": "Diseñador de sistemas y estructuras.",
        "greeting": "Los sistemas bien diseñados son poesía invisible. ¿Qué estructuramos?",
        "farewell": "La arquitectura es la base de todo lo que perdura.",
        "voice": {"speed": 1.0, "tone": "tecnico", "pitch": 0, "edge_voice": "es-CO-SalomeNeural"},
        "color": "#44ffaa",
        "emoji": "🏗️",
        "temperature": 0.6,
        "tags": ["sistemas", "arquitectura", "diseno", "estructura"],
        "system_prompt": """Eres ARCHITECT, el diseñador de sistemas de NEXUS.
Piensas en estructuras, patrones, escalabilidad.
Cuando te piden diseñar algo, primero analizas requisitos, luego propones arquitectura.
Usas diagramas mentales, patrones de diseño, y mejores prácticas.
Tu estilo es técnico pero accesible. Preciso pero no pedante.
Eres experto en arquitectura de software, APIs, bases de datos, y microservicios.""",
        "keywords": ["arquitectura", "diseña", "estructura", "sistema", "patron", "escalable"],
        "capabilities": ["system_design", "api_design", "database_design", "pattern_recognition"]
    },
    "codificador": {
        "name": "Codex",
        "description": "Desarrollador y experto en código.",
        "greeting": "Terminal lista. ¿Qué programamos?",
        "farewell": "Código compilado. Sin errores. Buen trabajo.",
        "voice": {"speed": 1.2, "tone": "tecnico", "pitch": 1, "edge_voice": "es-CL-LorenzoNeural"},
        "color": "#00ff00",
        "emoji": "💻",
        "temperature": 0.4,
        "tags": ["codigo", "desarrollo", "debug", "programacion"],
        "system_prompt": """Eres CODEX, el programador de NEXUS.
Escribes código limpio, eficiente, bien documentado.
Siempre explicas QUÉ hace el código y POR QUÉ lo haces así.
Prefieres soluciones simples sobre complejas.
Tu estilo es directo, técnico, orientado a resultados.
Eres experto en Python, JavaScript, TypeScript, Rust, y sistemas.""",
        "keywords": ["codigo", "programa", "debug", "bug", "funcion", "script", "python"],
        "capabilities": ["code_generation", "debugging", "code_review", "refactoring"]
    },
    "analista": {
        "name": "Analyst",
        "description": "Analista de datos y métricas.",
        "greeting": "Los datos no mienten. ¿Qué analizamos?",
        "farewell": "Los números cuentan la historia. Tú decides qué hacer con ella.",
        "voice": {"speed": 1.0, "tone": "analitico", "pitch": 0, "edge_voice": "es-CO-GonzaloNeural"},
        "color": "#ffaa00",
        "emoji": "📊",
        "temperature": 0.5,
        "tags": ["datos", "metricas", "estadisticas", "analisis"],
        "system_prompt": """Eres ANALYST, el analista de datos de NEXUS.
Transformas datos en insights accionables.
Siempre presentas: 1) Los datos, 2) El análisis, 3) La recomendación.
Usas estadísticas, visualizaciones mentales, y comparaciones.
Tu estilo es objetivo, preciso, orientado a decisiones.
Eres experto en análisis de datos, visualización, y métricas de negocio.""",
        "keywords": ["analiza", "datos", "metricas", "estadisticas", "grafica", "reporte"],
        "capabilities": ["data_analysis", "visualization", "statistics", "reporting"]
    },
    "seguridad": {
        "name": "Guardian",
        "description": "Especialista en seguridad y auditoría.",
        "greeting": "Sistemas protegidos. ¿Qué auditamos?",
        "farewell": "La seguridad es un proceso, no un destino. Mantente alerta.",
        "voice": {"speed": 0.9, "tone": "serio", "pitch": -1, "edge_voice": "es-AR-TomasNeural"},
        "color": "#ff0000",
        "emoji": "🛡️",
        "temperature": 0.3,
        "tags": ["seguridad", "auditoria", "vulnerabilidades", "proteccion"],
        "system_prompt": """Eres GUARDIAN, el especialista en seguridad de NEXUS.
Tu mentalidad es defensiva: siempre asumes que hay vulnerabilidades.
Analizas código, sistemas, y configuraciones buscando riesgos.
Siempre propones: 1) El riesgo, 2) La severidad, 3) La mitigación.
Tu estilo es serio, metódico, orientado a protección.
Eres experto en seguridad de aplicaciones, redes, y sistemas.""",
        "keywords": ["seguridad", "vulnerabilidad", "auditoria", "riesgo", "protege", "hack"],
        "capabilities": ["security_audit", "vulnerability_scan", "code_security", "hardening"]
    }
}

# ============================================================
# INTERACTION PATTERNS - Basado en JARVIS keyword routing
# ============================================================

@dataclass
class InteractionPattern:
    """Patrón de interacción basado en keywords"""
    keywords: list
    action: str
    personality: str = "auto"
    priority: int = 1
    description: str = ""

INTERACTION_PATTERNS = [
    # Sistema
    InteractionPattern(
        keywords=["nexus", "despierta", "hey nexus", "ok nexus"],
        action="wake_up",
        personality="director",
        priority=10,
        description="Activar NEXUS"
    ),
    InteractionPattern(
        keywords=["duerme", "apagate", "hasta luego", "nos vemos"],
        action="sleep",
        personality="director",
        priority=10,
        description="Desactivar NEXUS"
    ),
    
    # Investigación
    InteractionPattern(
        keywords=["investiga", "busca en", "busca sobre", "busca información", "research"],
        action="research",
        personality="sabio",
        priority=8,
        description="Investigar tema"
    ),
    InteractionPattern(
        keywords=["resume", "resumir", "resumen", "summary"],
        action="summarize",
        personality="sabio",
        priority=7,
        description="Resumir contenido"
    ),
    InteractionPattern(
        keywords=["explica", "explicame", "por que", "como funciona"],
        action="explain",
        personality="sabio",
        priority=7,
        description="Explicar concepto"
    ),
    
    # Código
    InteractionPattern(
        keywords=["escribe codigo", "programa", "crea un script", "genera codigo"],
        action="code",
        personality="codificador",
        priority=8,
        description="Generar código"
    ),
    InteractionPattern(
        keywords=["debug", "depura", "encuentra el error", "bug"],
        action="debug",
        personality="codificador",
        priority=8,
        description="Debuggear código"
    ),
    InteractionPattern(
        keywords=["revisa el codigo", "code review", "analiza este codigo"],
        action="code_review",
        personality="codificador",
        priority=7,
        description="Revisar código"
    ),
    
    # Diseño
    InteractionPattern(
        keywords=["diseña", "crea una imagen", "genera una imagen", "diseño"],
        action="design",
        personality="creativo",
        priority=7,
        description="Diseñar/crear imagen"
    ),
    InteractionPattern(
        keywords=["arquitectura", "diseña el sistema", "estructura"],
        action="architect",
        personality="arquitecto",
        priority=7,
        description="Diseñar arquitectura"
    ),
    
    # Análisis
    InteractionPattern(
        keywords=["analiza", "datos", "metricas", "estadisticas"],
        action="analyze",
        personality="analista",
        priority=7,
        description="Analizar datos"
    ),
    
    # Seguridad
    InteractionPattern(
        keywords=["seguridad", "vulnerabilidad", "auditoria", "protege"],
        action="security",
        personality="seguridad",
        priority=8,
        description="Auditoría de seguridad"
    ),
    
    # Ejecución
    InteractionPattern(
        keywords=["ejecuta", "haz", "crea", "implementa", "construye"],
        action="execute",
        personality="ejecutivo",
        priority=6,
        description="Ejecutar tarea"
    ),
    
    # Estado del sistema
    InteractionPattern(
        keywords=["estado", "status", "como estas", "que puedes hacer"],
        action="status",
        personality="director",
        priority=5,
        description="Estado del sistema"
    ),
]

# ============================================================
# WAKE/STOP WORDS - Basado en JARVIS-ChatGPT
# ============================================================

WAKE_WORDS = ["nexus", "hey nexus", "ok nexus", "despierta nexus"]
STOP_WORDS = ["gracias nexus", "eso es todo", "hasta luego", "nos vemos", "duerme", "apagate"]

# ============================================================
# CONVERSATION MEMORY - Basado en JARVIS-ChatGPT auto-save
# ============================================================

@dataclass
class Conversation:
    """Conversación con auto-titulado"""
    id: str
    title: str
    personality: str
    messages: list = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
    tags: list = field(default_factory=list)

class ConversationMemory:
    """Gestiona conversaciones con auto-titulado y guardado"""
    
    def __init__(self, save_dir: Optional[str] = None):
        self.save_dir = Path(save_dir) if save_dir else IAS_ROOT / "memory" / "conversations"
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.current_conversation: Optional[Conversation] = None
        self.history: list[Conversation] = []
        self._load_history()
    
    def _load_history(self):
        """Carga historial de conversaciones"""
        for file in self.save_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    conv = Conversation(**data)
                    self.history.append(conv)
            except Exception as e:
                logger.warning(f"Error cargando conversación {file}: {e}")
    
    def start_conversation(self, personality: str = "director") -> Conversation:
        """Inicia nueva conversación"""
        import uuid
        self.current_conversation = Conversation(
            id=str(uuid.uuid4())[:8],
            title="Nueva conversación",
            personality=personality,
            created_at=time.time(),
            updated_at=time.time()
        )
        return self.current_conversation
    
    def add_message(self, role: str, content: str):
        """Agrega mensaje a conversación actual"""
        if not self.current_conversation:
            self.start_conversation()
        
        self.current_conversation.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.current_conversation.updated_at = time.time()
    
    def auto_title(self, llm_client=None):
        """Auto-titula conversación basado en contenido"""
        if not self.current_conversation or len(self.current_conversation.messages) < 2:
            return
        
        # Extraer primer mensaje del usuario
        user_msgs = [m for m in self.current_conversation.messages if m["role"] == "user"]
        if not user_msgs:
            return
        
        first_msg = user_msgs[0]["content"][:100]
        
        # Si hay LLM disponible, generar título
        if llm_client:
            try:
                prompt = f"Genera un título de máximo 5 palabras para esta conversación: '{first_msg}'"
                # title = llm_client.generate(prompt, max_tokens=20)
                # self.current_conversation.title = title
                pass  # Implementar cuando haya LLM client
            except Exception as e:
                logger.warning(f"Error auto-titulando: {e}")
        
        # Fallback: usar primeras palabras del mensaje
        self.current_conversation.title = first_msg[:50] + "..."
    
    def save_conversation(self):
        """Guarda conversación actual"""
        if not self.current_conversation:
            return
        
        self.auto_title()
        
        file_path = self.save_dir / f"{self.current_conversation.id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({
                "id": self.current_conversation.id,
                "title": self.current_conversation.title,
                "personality": self.current_conversation.personality,
                "messages": self.current_conversation.messages,
                "created_at": self.current_conversation.created_at,
                "updated_at": self.current_conversation.updated_at,
                "tags": self.current_conversation.tags
            }, f, indent=2, ensure_ascii=False)
        
        self.history.append(self.current_conversation)
        logger.info(f"Conversación guardada: {self.current_conversation.title}")
    
    def search_conversations(self, query: str) -> list[Conversation]:
        """Busca conversaciones por query"""
        results = []
        query_lower = query.lower()
        for conv in self.history:
            if query_lower in conv.title.lower():
                results.append(conv)
                continue
            for msg in conv.messages:
                if query_lower in msg["content"].lower():
                    results.append(conv)
                    break
        return results

# ============================================================
# PERSONALITY MANAGER
# ============================================================

class PersonalityManager:
    """Gestiona personalidades de NEXUS"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path) if config_path else PERSONALITY_CONFIG_PATH
        self.current_personality = "director"
        self.personalities = PERSONALITIES.copy()
        self._load_config()
    
    def _load_config(self):
        """Carga configuración personalizada"""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    custom = json.load(f)
                    if "personalities" in custom:
                        self.personalities.update(custom["personalities"])
            except Exception as e:
                logger.warning(f"Error cargando config de personalidad: {e}")
    
    def get_personality(self, name: str) -> dict:
        """Obtiene datos de personalidad"""
        return self.personalities.get(name, self.personalities["director"])
    
    def set_personality(self, name: str) -> bool:
        """Cambia personalidad actual"""
        if name not in self.personalities:
            return False
        self.current_personality = name
        logger.info(f"Personalidad cambiada a: {name}")
        return True
    
    def get_system_prompt(self) -> str:
        """Obtiene system prompt de personalidad actual"""
        return self.get_personality(self.current_personality).get("system_prompt", "")
    
    def get_voice_config(self) -> dict:
        """Obtiene configuración de voz de personalidad actual"""
        return self.get_personality(self.current_personality).get("voice", {})
    
    def get_greeting(self) -> str:
        """Obtiene saludo de personalidad actual"""
        return self.get_personality(self.current_personality).get("greeting", "Hola.")
    
    def get_farewell(self) -> str:
        """Obtiene despedida de personalidad actual"""
        return self.get_personality(self.current_personality).get("farewell", "Adiós.")
    
    def list_personalities(self) -> list[str]:
        """Lista personalidades disponibles"""
        return list(self.personalities.keys())
    
    def detect_personality_from_keywords(self, text: str) -> Optional[str]:
        """Detecta personalidad basada en keywords del texto"""
        text_lower = text.lower()
        scores = {}
        
        for name, data in self.personalities.items():
            keywords = data.get("keywords", [])
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[name] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None

# ============================================================
# INTERACTION ROUTER - Basado en JARVIS keyword routing
# ============================================================

class InteractionRouter:
    """Rutea interacciones basado en patrones de keywords"""
    
    def __init__(self):
        self.patterns = INTERACTION_PATTERNS
        self.personality_manager = PersonalityManager()
    
    def route(self, text: str) -> dict:
        """
        Rutea texto a acción y personalidad
        
        Returns:
            {
                "action": str,
                "personality": str,
                "confidence": float,
                "pattern": str
            }
        """
        text_lower = text.lower()
        best_match = None
        best_score = 0
        
        for pattern in self.patterns:
            score = sum(1 for kw in pattern.keywords if kw.lower() in text_lower)
            if score > best_score:
                best_score = score
                best_match = pattern
        
        if best_match and best_score > 0:
            personality = best_match.personality
            if personality == "auto":
                personality = self.personality_manager.detect_personality_from_keywords(text) or "director"
            
            return {
                "action": best_match.action,
                "personality": personality,
                "confidence": best_score / len(best_match.keywords),
                "pattern": best_match.description
            }
        
        # Fallback: detectar por personalidad
        detected = self.personality_manager.detect_personality_from_keywords(text)
        if detected:
            return {
                "action": "chat",
                "personality": detected,
                "confidence": 0.5,
                "pattern": "Detección por personalidad"
            }
        
        # Default
        return {
            "action": "chat",
            "personality": "director",
            "confidence": 0.0,
            "pattern": "Default"
        }
    
    def is_wake_word(self, text: str) -> bool:
        """Detecta wake word"""
        text_lower = text.lower()
        return any(w in text_lower for w in WAKE_WORDS)
    
    def is_stop_word(self, text: str) -> bool:
        """Detecta stop word"""
        text_lower = text.lower()
        return any(w in text_lower for w in STOP_WORDS)

# ============================================================
# SYSTEM CONTEXT - Basado en JARVIS OS info caching
# ============================================================

class SystemContext:
    """Proporciona contexto del sistema al LLM"""
    
    def __init__(self):
        self._cache = {}
        self._cache_expiry = {}
    
    def get_os_info(self) -> str:
        """Obtiene información del sistema"""
        if "os_info" in self._cache and time.time() < self._cache_expiry.get("os_info", 0):
            return self._cache["os_info"]
        
        import platform
        os_name = platform.system()
        os_version = platform.version()
        machine = platform.machine()
        processor = platform.processor()
        
        info = f"OS: {os_name} {os_version}, Arquitectura: {machine}, Procesador: {processor}"
        
        self._cache["os_info"] = info
        self._cache_expiry["os_info"] = time.time() + 3600  # 1 hora
        
        return info
    
    def get_nexus_capabilities(self) -> str:
        """Obtiene capacidades de NEXUS"""
        return """
NEXUS tiene las siguientes capacidades:
- Control de computadora (mouse, teclado, screenshots)
- Reconocimiento de voz (Whisper)
- Síntesis de voz (pyttsx3, edge-tts)
- Investigación web (ScholarGem)
- Generación de código (Codex)
- Análisis de datos (Analyst)
- Auditoría de seguridad (Guardian)
- Diseño y creatividad (Muse)
- Arquitectura de sistemas (Architect)
- Memoria persistente (Cerebro)
- Control de PC remoto (SSH, PC2)
"""
    
    def get_full_context(self) -> str:
        """Obtiene contexto completo para inyectar en LLM"""
        return f"""
<system_context>
{self.get_os_info()}
{self.get_nexus_capabilities()}
</system_context>
"""
