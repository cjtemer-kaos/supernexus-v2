"""
Safety-First API Defaults - F4

Protecciones de seguridad para la API de SuperNEXUS:
- Rate Limiter (sliding window por IP)
- Circuit Breaker (evita llamadas a servicios caídos)
- Timeout Manager (timeouts configurables por servicio)
- Fallback Chain (cadena de fallback para modelos)
- Request Validator (validar tamaño y contenido)
"""

import time
import asyncio
import logging
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("nexus-safety")


# ============================================================
# RATE LIMITER - Sliding window por IP
# ============================================================

@dataclass
class RateLimitConfig:
    max_requests: int = 30
    window_seconds: int = 60
    burst_limit: int = 5
    burst_window: int = 5


class RateLimiter:
    """Rate limiter con sliding window + burst detection"""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._burst: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> tuple[bool, Dict]:
        now = time.time()

        # Limpiar ventanas expiradas
        window_start = now - self.config.window_seconds
        self._requests[client_id] = [
            t for t in self._requests[client_id] if t > window_start
        ]

        burst_start = now - self.config.burst_window
        self._burst[client_id] = [
            t for t in self._burst[client_id] if t > burst_start
        ]

        # Verificar burst
        if len(self._burst[client_id]) >= self.config.burst_limit:
            return False, {
                "reason": "burst_limit_exceeded",
                "retry_after": self.config.burst_window,
            }

        # Verificar rate limit
        if len(self._requests[client_id]) >= self.config.max_requests:
            oldest = self._requests[client_id][0]
            retry_after = int(self.config.window_seconds - (now - oldest))
            return False, {
                "reason": "rate_limit_exceeded",
                "retry_after": max(1, retry_after),
            }

        # Registrar request
        self._requests[client_id].append(now)
        self._burst[client_id].append(now)

        return True, {
            "remaining": self.config.max_requests - len(self._requests[client_id]),
            "reset_in": self.config.window_seconds,
        }

    def reset(self, client_id: str = None):
        if client_id:
            self._requests.pop(client_id, None)
            self._burst.pop(client_id, None)
        else:
            self._requests.clear()
            self._burst.clear()


# ============================================================
# CIRCUIT BREAKER - Protege servicios externos
# ============================================================

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: int = 60
    half_open_max_calls: int = 3


class CircuitBreaker:
    """Circuit breaker para servicios externos"""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.last_state_change = time.time()
        self._half_open_calls = 0

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self.last_state_change = time.time()
                logger.info(f"Circuit {self.name}: OPEN → HALF_OPEN")
                return True
            return False

        # HALF_OPEN
        return self._half_open_calls < self.config.half_open_max_calls

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = time.time()
                logger.info(f"Circuit {self.name}: HALF_OPEN → CLOSED")
        else:
            self.failure_count = max(0, self.failure_count - 1)
            self.success_count += 1

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(f"Circuit {self.name}: HALF_OPEN → OPEN")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(
                f"Circuit {self.name}: CLOSED → OPEN "
                f"({self.failure_count} failures)"
            )

    def get_status(self) -> Dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time,
        }


# ============================================================
# TIMEOUT MANAGER - Timeouts configurables por servicio
# ============================================================

@dataclass
class TimeoutConfig:
    ollama_chat: float = 120.0
    ollama_vision: float = 180.0
    ollama_generate: float = 60.0
    pc2_remote: float = 30.0
    http_request: float = 30.0
    websocket: float = 10.0
    file_operation: float = 5.0
    database: float = 10.0


class TimeoutManager:
    """Gestiona timeouts por tipo de servicio"""

    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self._timeouts: Dict[str, float] = {
            "ollama_chat": self.config.ollama_chat,
            "ollama_vision": self.config.ollama_vision,
            "ollama_generate": self.config.ollama_generate,
            "pc2_remote": self.config.pc2_remote,
            "http_request": self.config.http_request,
            "websocket": self.config.websocket,
            "file_operation": self.config.file_operation,
            "database": self.config.database,
        }

    def get_timeout(self, service: str) -> float:
        return self._timeouts.get(service, self.config.http_request)

    def set_timeout(self, service: str, seconds: float):
        self._timeouts[service] = seconds

    async def execute_with_timeout(self, service: str, coro, *args, **kwargs):
        timeout = self.get_timeout(service)
        try:
            return await asyncio.wait_for(coro(*args, **kwargs), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout en {service} ({timeout}s)")
            raise


# ============================================================
# FALLBACK CHAIN - Cadena de fallback para modelos
# ============================================================

@dataclass
class ModelFallback:
    primary: str
    fallbacks: List[str]
    max_retries: int = 2


class FallbackChain:
    """Cadena de fallback para modelos de IA"""

    def __init__(self):
        self._chains: Dict[str, ModelFallback] = {
            "chat": ModelFallback(
                primary="qwen3.6:latest",
                fallbacks=["llama3.2:3b", "nemotron-3-nano:4b"],
            ),
            "vision": ModelFallback(
                primary="qwen2.5vl:7b",
                fallbacks=["llava:7b"],
            ),
            "code": ModelFallback(
                primary="qwen2.5-coder:7b",
                fallbacks=["deepseek-coder:6.7b", "llama3.2:3b"],
            ),
        }

    def get_chain(self, task_type: str) -> ModelFallback:
        return self._chains.get(
            task_type,
            ModelFallback(primary="qwen3.6:latest", fallbacks=["llama3.2:3b"]),
        )

    def set_chain(self, task_type: str, chain: ModelFallback):
        self._chains[task_type] = chain

    def get_all_models(self, task_type: str) -> List[str]:
        chain = self.get_chain(task_type)
        return [chain.primary] + chain.fallbacks


# ============================================================
# REQUEST VALIDATOR - Validar requests
# ============================================================

@dataclass
class RequestValidationConfig:
    max_message_length: int = 4000
    max_images: int = 4
    max_image_size_kb: int = 2048
    max_files: int = 5
    max_file_size_mb: int = 10
    blocked_patterns: List[str] = field(default_factory=lambda: [])


class RequestValidator:
    """Valida requests entrantes"""

    def __init__(self, config: Optional[RequestValidationConfig] = None):
        self.config = config or RequestValidationConfig()

    def validate(self, data: Dict) -> tuple[bool, Optional[str]]:
        message = data.get("message", "")

        if len(message) > self.config.max_message_length:
            return False, f"Mensaje demasiado largo ({len(message)} chars, max {self.config.max_message_length})"

        images = data.get("images", [])
        if len(images) > self.config.max_images:
            return False, f"Demasiadas imágenes ({len(images)}, max {self.config.max_images})"

        for i, img in enumerate(images):
            if len(img) > self.config.max_image_size_kb * 1024:
                return False, f"Imagen {i} demasiado grande"

        files = data.get("files", [])
        if len(files) > self.config.max_files:
            return False, f"Demasiados archivos ({len(files)}, max {self.config.max_files})"

        return True, None


# ============================================================
# SAFETY MANAGER - Orquestador central
# ============================================================

class SafetyManager:
    """Orquestador central de todas las protecciones de seguridad"""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            "ollama": CircuitBreaker("ollama"),
            "pc2": CircuitBreaker("pc2"),
            "vision": CircuitBreaker("vision"),
            "database": CircuitBreaker("database"),
        }
        self.timeout_manager = TimeoutManager()
        self.fallback_chain = FallbackChain()
        self.request_validator = RequestValidator()

    def get_client_ip(self, request) -> str:
        """Extrae IP del request, respetando X-Forwarded-For"""
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[0].strip()
        peername = request.transport.get_extra_info("peername")
        if peername:
            return peername[0]
        return "unknown"

    def check_rate_limit(self, client_id: str) -> tuple[bool, Dict]:
        return self.rate_limiter.is_allowed(client_id)

    def can_use_service(self, service: str) -> bool:
        cb = self.circuit_breakers.get(service)
        if cb:
            return cb.can_execute()
        return True

    def record_service_success(self, service: str):
        cb = self.circuit_breakers.get(service)
        if cb:
            cb.record_success()

    def record_service_failure(self, service: str):
        cb = self.circuit_breakers.get(service)
        if cb:
            cb.record_failure()

    def get_status(self) -> Dict:
        return {
            "circuit_breakers": {
                name: cb.get_status()
                for name, cb in self.circuit_breakers.items()
            },
            "rate_limit_config": {
                "max_requests": self.rate_limiter.config.max_requests,
                "window_seconds": self.rate_limiter.config.window_seconds,
            },
            "timeouts": {
                service: self.timeout_manager.get_timeout(service)
                for service in [
                    "ollama_chat", "ollama_vision", "pc2_remote", "http_request"
                ]
            },
            "fallback_chains": {
                task_type: {
                    "primary": chain.primary,
                    "fallbacks": chain.fallbacks,
                }
                for task_type, chain in self.fallback_chain._chains.items()
            },
        }

    def check_input(self, text: str) -> Dict:
        """Validate input text for security risks"""
        risks = []
        risk_level = "safe"
        lower = text.lower()
        if "<script" in lower or "javascript:" in lower:
            risks.append("XSS pattern detected")
            risk_level = "high"
        if any(kw in lower for kw in ["drop table", "delete from", "insert into", "union select"]):
            risks.append("SQL injection pattern")
            risk_level = "high" if risk_level != "high" else risk_level
        if "password" in lower and "token" in lower:
            risks.append("Potential credential exposure")
            risk_level = "medium" if risk_level == "safe" else risk_level
        return {"risk_level": risk_level, "reasons": risks, "sanitized": text}

    def check_output(self, text: str) -> Dict:
        """Validate output text for security risks"""
        risks = []
        risk_level = "safe"
        lower = text.lower()
        if any(kw in lower for kw in ["api_key", "secret_key", "password:", "token:"]):
            risks.append("Potential credential leak")
            risk_level = "high"
        return {"risk_level": risk_level, "reasons": risks, "sanitized": text}

    def check_command_safety(self, command: str) -> tuple[bool, Optional[str]]:
        """
        Analiza un comando para detectar posibles riesgos de seguridad e inyección (RCE).
        Retorna (is_safe, error_reason).
        """
        if not command:
            return True, None

        cmd_lower = command.lower().strip()
        import re

        # 1. Caracteres peligrosos para concatenación / encadenamiento de comandos sin control
        dangerous_operators = [';', '&&', '||', '`', '$(']
        for op in dangerous_operators:
            if op in command:
                return False, f"Concatenación de comandos prohibida: metacaracter '{op}' detectado"

        # Permitir pipes '|' y '&' solo si no intentan inyectar comandos maliciosos comunes.
        if '|' in command or '&' in command:
            parts = re.split(r'[|&]', command)
            for part in parts[1:]:
                part_clean = part.strip().lower()
                if any(kw in part_clean for kw in ["curl", "wget", "rm", "del", "sh", "bash", "cmd", "powershell", "python"]):
                    return False, "Inyección de comandos sospechosa tras operador de redirección detectada"

        # 2. Comandos y palabras clave extremadamente destructivas o sospechosas (Blocklist)
        destructive_patterns = [
            r"\brm\s+-[rfv]*\s*/",  # rm -rf /
            r"\brmdir\s+/[sq]*\s*[a-zA-Z]:",  # rmdir /s C:
            r"\bdel\s+/[sfq]*\s*[a-zA-Z]:",  # del /s C:
            r"\brd\s+/[sq]*\s*[a-zA-Z]:",  # rd /s C:
            r"\bformat\s+[a-zA-Z]:",  # format C:
            r"\bmkfs\b",
        ]
        for pattern in destructive_patterns:
            if re.search(pattern, cmd_lower):
                return False, "Comando destructivo detectado"

        # 3. Comandos de descarga y ejecución remota sin control
        remote_execution_keywords = ["curl", "wget", "iwr", "irm", "http://", "https://"]
        if any(kw in cmd_lower for kw in remote_execution_keywords):
            if any(pipe_kw in cmd_lower for pipe_kw in ["| sh", "|bash", "|cmd", "|powershell", "|pwsh", "iex"]):
                return False, "Descarga y ejecución remota de scripts bloqueada por seguridad"

        # 4. Evasión de PowerShell / CMD y manipulación de cuentas/privilegios
        evasion_keywords = ["-encodedcommand", "-enc", "bypass", "exec bypass", "net user", "net localgroup", "netsh"]
        if any(kw in cmd_lower for kw in evasion_keywords):
            return False, "Evasión de políticas de ejecución o comando administrativo bloqueado"

        return True, None

    def reset(self):
        """Reset all circuit breakers and rate limiters"""
        for cb in self.circuit_breakers.values():
            cb.reset()
        self.rate_limiter.reset()
