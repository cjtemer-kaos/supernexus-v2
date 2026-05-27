#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Upstash Skill - Serverless Redis
Uso: Operaciones de caché y almacenamiento con Upstash Redis
"""
import json
import os
import requests
from typing import Any, Optional

class UpstashSkill:
    def __init__(self, redis_url: str = "", token: str = ""):
        self.name = "UpstashSkill"
        self.redis_url = redis_url or os.environ.get("UPSTASH_REDIS_URL", "")
        self.token = token or os.environ.get("UPSTASH_TOKEN", "")
        self.available = bool(self.redis_url and self.token)
    
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _request(self, command: list) -> Any:
        """Ejecuta un comando Redis via REST API"""
        if not self.available:
            return "[ERROR] Configurá UPSTASH_REDIS_URL y UPSTASH_TOKEN"
        
        try:
            r = requests.post(
                self.redis_url,
                json=command,
                headers=self._headers(),
                timeout=10
            )
            if r.status_code == 200:
                return r.json().get("result")
            return f"[ERROR] {r.status_code}: {r.text}"
        except Exception as e:
            return f"[ERROR] {e}"
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> str:
        """GUARDA un valor"""
        if ttl:
            return self._request(["SETEX", key, ttl, json.dumps(value)])
        return self._request(["SET", key, json.dumps(value)])
    
    def get(self, key: str) -> Any:
        """Obtiene un valor"""
        result = self._request(["GET", key])
        if isinstance(result, str):
            try:
                return json.loads(result)
            except:
                return result
        return result
    
    def delete(self, key: str) -> str:
        """Elimina una clave"""
        return self._request(["DEL", key])
    
    def exists(self, key: str) -> bool:
        """Verifica si existe una clave"""
        result = self._request(["EXISTS", key])
        return result == 1 if isinstance(result, int) else False
    
    def incr(self, key: str) -> int:
        """Incrementa un contador"""
        result = self._request(["INCR", key])
        return result if isinstance(result, int) else 0
    
    def expire(self, key: str, seconds: int) -> str:
        """Establece tiempo de expiración"""
        return self._request(["EXPIRE", key, seconds])
    
    def keys(self, pattern: str = "*") -> list:
        """Lista claves que coinciden con el patrón"""
        result = self._request(["KEYS", pattern])
        return result if isinstance(result, list) else []
    
    def flushall(self) -> str:
        """Elimina todas las claves (¡Cuidado!)"""
        return self._request(["FLUSHALL"])
    
    def cache_wrapper(self, key: str, func, ttl: int = 3600):
        """Wrapper para caché: ejecuta func si no hay caché"""
        cached = self.get(key)
        if cached is not None:
            return cached
        result = func()
        self.set(key, result, ttl)
        return result
    
    def generate_setup(self) -> str:
        """Genera código de configuración"""
        code = f"""import {{ Redis }} from '@upstash/redis';

const redis = new Redis({{
  url: '{self.redis_url or 'TU_REDIS_URL'}',
  token: '{self.token or 'TU_TOKEN'}',
}});

// Ejemplo de uso:
await redis.set('key', 'value');
const value = await redis.get('key');
console.log(value); // 'value'
"""
        return f"[CODE]\n{code}"
    
    def generate_env_example(self) -> str:
        return """UPSTASH_REDIS_URL=https://tu-endpoint.upstash.io
UPSTASH_TOKEN=tu_token_aqui
"""
    
    def info(self) -> dict:
        status = "Conectado" if self.available else "No configurado"
        return {
            "skill": self.name,
            "status": status,
            "url_configured": bool(self.redis_url),
            "install": "npm install @upstash/redis",
            "docs": "https://docs.upstash.com/redis"
        }

if __name__ == "__main__":
    import os
    skill = UpstashSkill()
    print(json.dumps(skill.info(), indent=2))
