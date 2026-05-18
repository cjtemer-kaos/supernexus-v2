"""
Vision Configuration - Configuracion centralizada de vision
"""
import os

Remote Node_IP = os.getenv("SUPER_NEXUS_Remote Node_IP", "")

VISION_PROVIDERS = {
    "local": {
        "model": "qwen2.5vl:7b",
        "url": "http://localhost:11434",
        "fallback": "remote" if Remote Node_IP else None,
    },
    "claude": {
        "model": "claude-3-5-sonnet-20241022",
        "provider": "anthropic",
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "fallback": "local",
    },
}

if Remote Node_IP:
    VISION_PROVIDERS["remote"] = {
        "model": "qwen2.5vl:7b",
        "url": f"http://{Remote Node_IP}:11434",
        "fallback": "local",
    }

DEFAULT_VISION_PROVIDER = os.getenv("DEFAULT_VISION_PROVIDER", "local")

MAX_IMAGE_SIZE_MB = 20

SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "webp", "gif", "bmp"]

def get_vision_config(provider: str = None) -> dict:
    """Obtiene config del provider"""
    if provider is None:
        provider = DEFAULT_VISION_PROVIDER
    return VISION_PROVIDERS.get(provider, VISION_PROVIDERS["local"])

def get_all_providers() -> dict:
    """Lista todos los providers disponibles"""
    return {k: v.get("model", "unknown") for k, v in VISION_PROVIDERS.items()}
