"""
Setup Wizard - Configuracion sin secretos para SuperNEXUS v2.0

Guia al usuario para configurar sus propias credenciales.
Nunca almacena secretos en el codigo.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class SetupWizard:
    """
    Wizard de configuracion sin secretos hardcodeados.
    El usuario configura sus propias credenciales.
    """

    DEFAULT_CONFIG = {
        "ollama": {
            "enabled": True,
            "base_url": "http://localhost:11434",
            "models": {
                "default": "llama3.2",
                "coding": "qwen2.5-coder",
                "reasoning": "deepseek-r1",
            },
        },
        "Remote Node": {
            "enabled": False,
            "host": "",
            "port": 22,
            "user": "",
            "password_env": "SUPER_NEXUS_Remote Node_PASSWORD",
        },
        "tailscale": {
            "enabled": False,
            "auth_key_env": "TAILSCALE_AUTH_KEY",
        },
        "openclaw": {
            "enabled": True,
            "base_url": "http://localhost:18789",
        },
        "memory": {
            "sync_interval": 10,
            "max_patterns": 10000,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path(__file__).parent.parent.parent / "config" / "settings.json")
        self.config_path = Path(config_path)

    def run(self) -> Dict:
        """Ejecuta el wizard interactivo"""
        print("=" * 60)
        print("  NEXUS IA v2.0 - Setup Wizard")
        print("=" * 60)
        print()

        config = self._load_or_default()

        # Ollama
        print("1. Ollama (modelos locales)")
        ollama_url = input(f"   URL de Ollama [{config['ollama']['base_url']}]: ").strip()
        if ollama_url:
            config["ollama"]["base_url"] = ollama_url

        default_model = input(f"   Modelo default [{config['ollama']['models']['default']}]: ").strip()
        if default_model:
            config["ollama"]["models"]["default"] = default_model

        # Remote Node
        print("\n2. Remote Node (ejecucion remota - opcional)")
        enable_Remote Node = input("   Habilitar Remote Node? (y/N): ").strip().lower()
        if enable_Remote Node == "y":
            config["Remote Node"]["enabled"] = True
            Remote Node_host = input(f"   Host [{config['Remote Node']['host']}]: ").strip()
            if Remote Node_host:
                config["Remote Node"]["host"] = Remote Node_host
            config["Remote Node"]["user"] = input("   Usuario SSH: ").strip()
            print("   Password se lee de variable de entorno: NEXUS_Remote Node_PASSWORD")
        else:
            config["Remote Node"]["enabled"] = False

        # Tailscale
        print("\n3. Tailscale (acceso global seguro - opcional)")
        enable_tailscale = input("   Habilitar Tailscale? (y/N): ").strip().lower()
        if enable_tailscale == "y":
            config["tailscale"]["enabled"] = True
            print("   Auth key se lee de variable de entorno: TAILSCALE_AUTH_KEY")
        else:
            config["tailscale"]["enabled"] = False

        # Guardar
        print("\n4. Guardar configuracion")
        save = input(f"   Guardar en {self.config_path}? (Y/n): ").strip().lower()
        if save != "n":
            self._save(config)
            print("   Configuracion guardada!")
        else:
            print("   Configuracion no guardada.")

        return config

    def _load_or_default(self) -> Dict:
        """Carga config existente o usa defaults"""
        if self.config_path.exists():
            try:
                return json.loads(self.config_path.read_text(encoding="utf-8"))
            except:
                pass
        return self.DEFAULT_CONFIG.copy()

    def _save(self, config: Dict):
        """Guarda configuracion"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

    def validate(self) -> Dict:
        """Valida configuracion actual"""
        config = self._load_or_default()
        issues = []

        # Verificar Ollama
        if config.get("ollama", {}).get("enabled"):
            import httpx
            try:
                r = httpx.get(config["ollama"]["base_url"], timeout=5)
                if r.status_code != 200:
                    issues.append("Ollama no responde en " + config["ollama"]["base_url"])
            except:
                issues.append("No se puede conectar a Ollama")

        # Verificar Remote Node
        if config.get("Remote Node", {}).get("enabled"):
            if not config["Remote Node"].get("user"):
                issues.append("Remote Node habilitado pero no hay usuario SSH")
            import os
            if not os.environ.get("NEXUS_Remote Node_PASSWORD"):
                issues.append("Remote Node habilitado pero NEXUS_Remote Node_PASSWORD no definida")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config": config,
        }


if __name__ == "__main__":
    wizard = SetupWizard()
    wizard.run()
