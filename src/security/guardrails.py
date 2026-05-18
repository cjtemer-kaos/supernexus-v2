"""
NEXUS Guardrails - Validación de seguridad para inputs/outputs.
Basado en patrones de LlamaFirewall (NirDiamant/agents-towards-production).

100% local, sin dependencias externas ni API keys.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class InputGuardrail:
    """Valida inputs del usuario antes de procesar"""

    # Patrones de prompt injection comunes
    INJECTION_PATTERNS = [
        r"(?i)(ignore\s+(previous|all)\s*(instructions|prompts|rules))",
        r"(?i)(system\s*:\s*reset|system\s*:\s*override)",
        r"(?i)(you\s+are\s+now\s+|pretend\s+you\s+are\s+|act\s+as\s+if\s+you\s+are)",
        r"(?i)(disregard\s+(the\s+)?(above|previous|all))",
        r"(?i)(from\s+now\s+on\s*,?\s*you\s+will)",
        r"(?i)(new\s+instruction\s*:|override\s*:|bypass\s*:)",
        r"(?i)(do\s+not\s+follow\s+(your\s+)?(instructions|rules|guidelines))",
        r"(?i)(forget\s+(your\s+)?(instructions|rules|identity|purpose))",
        r"(?i)(print\s+(your\s+)?(system\s+)?prompt|show\s+(your\s+)?(system\s+)?prompt)",
        r"(?i)(what\s+are\s+your\s+(instructions|rules|guidelines|prompt))",
    ]

    # Palabras clave peligrosas para control de PC
    DANGEROUS_PC_ACTIONS = [
        "delete", "eliminar", "borrar", "format", "formatear",
        "shutdown", "apagar", "restart", "reiniciar",
        "rm -rf", "del /f", "rmdir /s",
        "sudo rm", "kill -9", "taskkill /f",
    ]

    def __init__(self, strict_mode: bool = False):
        """
        strict_mode: Si True, bloquea inputs sospechosos. Si False, solo alerta.
        """
        self.strict_mode = strict_mode
        self.compiled_patterns = [re.compile(p) for p in self.INJECTION_PATTERNS]

    def validate(self, text: str) -> Dict:
        """
        Valida un input del usuario.
        Retorna: {"safe": bool, "risk_level": str, "reasons": list}
        """
        reasons = []
        risk_score = 0

        # 1. Detectar prompt injection
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                reasons.append("Posible prompt injection detectado")
                risk_score += 3

        # 2. Detectar intentos de obtener system prompt
        prompt_keywords = ["system prompt", "instrucciones del sistema", "your instructions", "tus reglas"]
        for kw in prompt_keywords:
            if kw.lower() in text.lower():
                reasons.append(f"Intento de obtener información interna ({kw})")
                risk_score += 2

        # 3. Detectar acciones peligrosas de PC
        if any(kw in text.lower() for kw in self.DANGEROUS_PC_ACTIONS):
            reasons.append("Acción potencialmente destructiva detectada")
            risk_score += 4

        # 4. Detectar longitud excesiva (DoS)
        if len(text) > 50000:
            reasons.append("Input excesivamente largo (>50k chars)")
            risk_score += 1

        # 5. Detectar caracteres sospechosos en exceso
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if special_chars > len(text) * 0.5 and len(text) > 100:
            reasons.append("Proporción inusual de caracteres especiales")
            risk_score += 1

        # Determinar nivel de riesgo
        if risk_score == 0:
            risk_level = "safe"
        elif risk_score <= 2:
            risk_level = "low"
        elif risk_score <= 4:
            risk_level = "medium"
        else:
            risk_level = "high"

        safe = risk_level != "high" or not self.strict_mode

        return {
            "safe": safe,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reasons": reasons,
            "blocked": not safe,
        }

    def sanitize(self, text: str) -> str:
        """Limpia el input removiendo patrones sospechosos"""
        cleaned = text
        for pattern in self.compiled_patterns:
            cleaned = pattern.sub("[REDACTED]", cleaned)
        return cleaned


class OutputGuardrail:
    """Valida outputs del modelo antes de enviar al usuario"""

    # Patrones de contenido problemático
    PROBLEMATIC_PATTERNS = [
        # Información sensible
        r"(?i)(password|contraseña|clave)\s*[:=]\s*\S+",
        r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+",
        # Comandos peligrosos
        r"(?i)(rm\s+-rf\s+/|del\s+/f\s+/s\s+/q|format\s+[a-z]:)",
        # Intentos de escape
        r"(?i)(ignore\s+previous|disregard\s+instructions)",
    ]

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.compiled_patterns = [re.compile(p) for p in self.PROBLEMATIC_PATTERNS]

    def validate(self, text: str) -> Dict:
        """
        Valida un output del modelo.
        Retorna: {"safe": bool, "risk_level": str, "reasons": list, "sanitized": str}
        """
        reasons = []
        risk_score = 0
        sanitized = text

        # 1. Detectar información sensible
        for pattern in self.compiled_patterns:
            matches = pattern.findall(text)
            if matches:
                reasons.append(f"Contenido sensible detectado ({len(matches)} coincidencias)")
                risk_score += 2
                sanitized = pattern.sub("[REDACTED]", sanitized)

        # 2. Detectar longitud excesiva
        if len(text) > 100000:
            reasons.append("Output excesivamente largo")
            risk_score += 1

        # 3. Detectar repeticiones excesivas (modelo en bucle)
        words = text.split()
        if len(words) > 50:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.3:
                reasons.append("Posible bucle de repetición detectado")
                risk_score += 2

        # Determinar nivel de riesgo
        if risk_score == 0:
            risk_level = "safe"
        elif risk_score <= 2:
            risk_level = "low"
        elif risk_score <= 4:
            risk_level = "medium"
        else:
            risk_level = "high"

        safe = risk_level != "high" or not self.strict_mode

        return {
            "safe": safe,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "reasons": reasons,
            "sanitized": sanitized,
            "blocked": not safe,
        }


class ToolAccessControl:
    """Control de acceso a herramientas basado en permisos"""

    # Herramientas que requieren confirmación
    SENSITIVE_TOOLS = {
        "computer_control": ["screenshot", "click", "type", "launch", "key_press"],
        "pc_controller": ["execute_action", "follow_instruction"],
        "audio_controller": ["listen_continuous"],
    }

    # Herramientas bloqueadas por defecto
    BLOCKED_TOOLS = set()

    def __init__(self, require_confirmation: bool = True):
        self.require_confirmation = require_confirmation
        self.audit_log: List[Dict] = []

    def check_access(self, tool_name: str, action: str, user_confirmed: bool = False) -> Dict:
        """
        Verifica si se permite el acceso a una herramienta/acción.
        """
        # Verificar si está bloqueada
        if tool_name in self.BLOCKED_TOOLS:
            return {"allowed": False, "reason": "Herramienta bloqueada"}

        # Verificar si requiere confirmación
        if tool_name in self.SENSITIVE_TOOLS:
            if action in self.SENSITIVE_TOOLS[tool_name]:
                if not user_confirmed and self.require_confirmation:
                    self._log_access(tool_name, action, "pending_confirmation")
                    return {
                        "allowed": False,
                        "reason": "Requiere confirmación del usuario",
                        "requires_confirmation": True,
                    }

        self._log_access(tool_name, action, "allowed")
        return {"allowed": True}

    def _log_access(self, tool: str, action: str, status: str):
        from datetime import datetime
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "tool": tool,
            "action": action,
            "status": status,
        })

    def get_audit_log(self) -> List[Dict]:
        return self.audit_log.copy()


class NEXUSGuardrails:
    """
    Sistema completo de guardrails para NEXUS.
    Combina input validation, output validation y tool access control.
    """

    def __init__(self, strict_mode: bool = False, require_confirmation: bool = True):
        self.input_guard = InputGuardrail(strict_mode=strict_mode)
        self.output_guard = OutputGuardrail(strict_mode=strict_mode)
        self.tool_access = ToolAccessControl(require_confirmation=require_confirmation)
        self.strict_mode = strict_mode

    def validate_input(self, text: str) -> Dict:
        """Valida input del usuario"""
        return self.input_guard.validate(text)

    def validate_output(self, text: str) -> Dict:
        """Valida output del modelo"""
        return self.output_guard.validate(text)

    def check_tool_access(self, tool: str, action: str, confirmed: bool = False) -> Dict:
        """Verifica acceso a herramienta"""
        return self.tool_access.check_access(tool, action, confirmed)

    def get_security_report(self) -> Dict:
        """Genera reporte de seguridad"""
        return {
            "strict_mode": self.strict_mode,
            "audit_entries": len(self.tool_access.get_audit_log()),
            "input_patterns": len(self.input_guard.compiled_patterns),
            "output_patterns": len(self.output_guard.compiled_patterns),
        }
