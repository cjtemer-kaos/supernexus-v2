"""
SecurityMiddleware - Ciberseguridad para SuperNEXUS v2.0

Características:
- Validación de inputs en todos los endpoints
- Rate limiting por IP y por usuario
- Auditoría de acceso con logs detallados
- Sanitización de datos sensibles
- Protección contra inyección de comandos
"""

import re
import time
import logging
import hashlib
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuración de rate limiting"""
    max_requests: int = 100
    window_seconds: float = 60.0
    block_duration: float = 300.0


@dataclass
class AuditLog:
    """Registro de auditoría"""
    timestamp: str
    ip: str
    user: str
    action: str
    endpoint: str
    status: str
    details: str = ""


class InputValidator:
    """Validación y sanitización de inputs"""
    
    MAX_INPUT_LENGTH = 10000
    MAX_FILE_SIZE = 50 * 1024 * 1024
    ALLOWED_CONTENT_TYPES = [
        "text/plain", "application/json", "image/png", "image/jpeg", "image/webp"
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r";\s*(rm|del|chmod|chown|sudo|wget|curl|nc|bash|sh|python|node|exec|eval)",
        r"\|\s*(rm|del|chmod|chown|sudo|wget|curl|nc|bash|sh|python|node|exec|eval)",
        r"`[^`]*`",
        r"\$\([^)]*\)",
        r"&&\s*(rm|del|chmod|chown|sudo)",
        r"\|\|\s*(rm|del|chmod|chown|sudo)",
    ]
    
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b\s+\d+=\d+)",
    ]
    
    @classmethod
    def validate_string(cls, value: str, max_length: int = None) -> str:
        """Valida y sanitiza string"""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        max_len = max_length or cls.MAX_INPUT_LENGTH
        if len(value) > max_len:
            raise ValueError(f"Input too long: {len(value)} > {max_len}")
        
        if cls.detect_command_injection(value):
            raise ValueError("Potential command injection detected")
        
        if cls.detect_sql_injection(value):
            raise ValueError("Potential SQL injection detected")
        
        return value.strip()
    
    @classmethod
    def validate_json(cls, data: Dict, required_fields: List[str] = None) -> Dict:
        """Valida estructura JSON"""
        if not isinstance(data, dict):
            raise ValueError("Input must be a JSON object")
        
        if required_fields:
            missing = [f for f in required_fields if f not in data]
            if missing:
                raise ValueError(f"Missing required fields: {missing}")
        
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = cls.validate_string(value)
        
        return data
    
    @classmethod
    def detect_command_injection(cls, value: str) -> bool:
        """Detecta patrones de inyección de comandos"""
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"Command injection pattern detected: {pattern}")
                return True
        return False
    
    @classmethod
    def detect_sql_injection(cls, value: str) -> bool:
        """Detecta patrones de inyección SQL"""
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                return True
        return False
    
    @classmethod
    def sanitize_path(cls, path: str) -> str:
        """Sanitiza ruta de archivo"""
        path = path.replace("..", "").replace("\\", "/")
        path = re.sub(r"[^\w\-\./]", "", path)
        return path
    
    @classmethod
    def validate_file_size(cls, size: int) -> bool:
        """Valida tamaño de archivo"""
        return size <= cls.MAX_FILE_SIZE
    
    @classmethod
    def validate_content_type(cls, content_type: str) -> bool:
        """Valida tipo de contenido"""
        return content_type in cls.ALLOWED_CONTENT_TYPES


class RateLimiter:
    """Rate limiting por IP y usuario"""
    
    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blocked: Dict[str, float] = {}
    
    def is_allowed(self, identifier: str) -> bool:
        """Verifica si una petición está permitida"""
        now = time.time()
        
        if identifier in self.blocked:
            if now - self.blocked[identifier] < self.config.block_duration:
                return False
            else:
                del self.blocked[identifier]
                self.requests[identifier] = []
        
        window_start = now - self.config.window_seconds
        self.requests[identifier] = [
            t for t in self.requests[identifier] if t > window_start
        ]
        
        if len(self.requests[identifier]) >= self.config.max_requests:
            self.blocked[identifier] = now
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        self.requests[identifier].append(now)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Obtiene peticiones restantes"""
        now = time.time()
        window_start = now - self.config.window_seconds
        
        current_requests = len([
            t for t in self.requests[identifier] if t > window_start
        ])
        
        return max(0, self.config.max_requests - current_requests)
    
    def reset(self, identifier: str = None):
        """Resetea rate limiter"""
        if identifier:
            self.requests.pop(identifier, None)
            self.blocked.pop(identifier, None)
        else:
            self.requests.clear()
            self.blocked.clear()


class AuditLogger:
    """Sistema de auditoría de acceso"""
    
    def __init__(self, max_logs: int = 10000):
        self.logs: List[AuditLog] = []
        self.max_logs = max_logs
    
    def log(
        self,
        action: str,
        endpoint: str,
        ip: str = "unknown",
        user: str = "anonymous",
        status: str = "success",
        details: str = ""
    ):
        """Registra acción"""
        log = AuditLog(
            timestamp=datetime.now().isoformat(),
            ip=ip,
            user=user,
            action=action,
            endpoint=endpoint,
            status=status,
            details=details,
        )
        
        self.logs.append(log)
        
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        if status == "failure":
            logger.warning(f"AUDIT: {action} failed for {user}@{ip}: {details}")
    
    def get_logs(
        self,
        user: str = None,
        ip: str = None,
        action: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Obtiene logs filtrados"""
        filtered = self.logs
        
        if user:
            filtered = [l for l in filtered if l.user == user]
        if ip:
            filtered = [l for l in filtered if l.ip == ip]
        if action:
            filtered = [l for l in filtered if l.action == action]
        
        return [
            {
                "timestamp": l.timestamp,
                "ip": l.ip,
                "user": l.user,
                "action": l.action,
                "endpoint": l.endpoint,
                "status": l.status,
                "details": l.details,
            }
            for l in filtered[-limit:]
        ]
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas de auditoría"""
        total = len(self.logs)
        successes = len([l for l in self.logs if l.status == "success"])
        failures = len([l for l in self.logs if l.status == "failure"])
        
        unique_users = len(set(l.user for l in self.logs))
        unique_ips = len(set(l.ip for l in self.logs))
        
        return {
            "total_logs": total,
            "successes": successes,
            "failures": failures,
            "unique_users": unique_users,
            "unique_ips": unique_ips,
        }


class SecurityMiddleware:
    """
    Middleware de seguridad unificado para SuperNEXUS v2.0
    
    Uso en FastAPI:
        from src.security.security_middleware import SecurityMiddleware
        
        security = SecurityMiddleware()
        
        @app.middleware("http")
        async def security_middleware(request, call_next):
            result = await security.process_request(request)
            if result.get("blocked"):
                return JSONResponse(status_code=429, content=result)
            response = await call_next(request)
            return response
    """
    
    def __init__(
        self,
        rate_limit_config: RateLimitConfig = None,
        enable_audit: bool = True,
        enable_input_validation: bool = True,
    ):
        self.rate_limiter = RateLimiter(rate_limit_config)
        self.audit_logger = AuditLogger() if enable_audit else None
        self.input_validator = InputValidator() if enable_input_validation else None
        self._api_keys: Dict[str, Dict] = {}
    
    def register_api_key(self, key: str, user: str, permissions: List[str] = None):
        """Registra clave API"""
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        self._api_keys[hashed_key] = {
            "user": user,
            "permissions": permissions or ["read", "write"],
            "created": datetime.now().isoformat(),
        }
    
    def validate_api_key(self, key: str) -> Optional[Dict]:
        """Valida clave API"""
        hashed_key = hashlib.sha256(key.encode()).hexdigest()
        return self._api_keys.get(hashed_key)
    
    async def process_request(self, request) -> Optional[Dict]:
        """Procesa petición con todas las capas de seguridad"""
        ip = request.client.host if hasattr(request, "client") else "unknown"
        endpoint = request.url.path
        
        if self.rate_limiter and not self.rate_limiter.is_allowed(ip):
            if self.audit_logger:
                self.audit_logger.log(
                    action="rate_limit_exceeded",
                    endpoint=endpoint,
                    ip=ip,
                    status="failure",
                    details="Rate limit exceeded",
                )
            return {
                "blocked": True,
                "status": 429,
                "message": "Rate limit exceeded. Try again later.",
            }
        
        if self.audit_logger:
            self.audit_logger.log(
                action="request",
                endpoint=endpoint,
                ip=ip,
                status="success",
            )
        
        return None
    
    def validate_input(self, data: Dict, required_fields: List[str] = None) -> Dict:
        """Valida input de petición"""
        if self.input_validator:
            return self.input_validator.validate_json(data, required_fields)
        return data
    
    def get_security_status(self) -> Dict:
        """Obtiene estado de seguridad"""
        status = {
            "rate_limiter": {
                "config": {
                    "max_requests": self.rate_limiter.config.max_requests,
                    "window_seconds": self.rate_limiter.config.window_seconds,
                }
            },
            "api_keys_registered": len(self._api_keys),
        }
        
        if self.audit_logger:
            status["audit"] = self.audit_logger.get_stats()
        
        return status
