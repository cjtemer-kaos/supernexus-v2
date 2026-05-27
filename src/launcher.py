"""
SuperNEXUS Launcher - Single entry point for the entire system

Usage:
    python -m supernexus          # Start everything
    python -m supernexus --no-ui  # Start without UI
    python -m supernexus --help   # Show help

What it does:
1. Auto-detects/creates Python venv
2. Auto-starts Ollama if not running
3. Auto-pulls required models
4. Starts backend server (port 9000)
5. Opens browser or launches Tauri app
6. Health checks all services
7. Graceful shutdown on exit
"""

import argparse
import asyncio
import logging
import os
import platform
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.ollama_manager import OllamaManager, REQUIRED_MODELS
from src.core.credential_manager import CredentialManager

logger = logging.getLogger("nexus-launcher")

# Default configuration
DEFAULT_BACKEND_PORT = int(os.environ.get("NEXUS_BACKEND_PORT", "9000"))
DEFAULT_UI_PORT = int(os.environ.get("NEXUS_UI_PORT", "3000"))
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")


class NexusLauncher:
    """
    Orchestrates the entire SuperNEXUS startup sequence.
    """

    def __init__(self, no_ui: bool = False, no_ollama: bool = False, port: int = None):
        self.no_ui = no_ui
        self.no_ollama = no_ollama
        self.backend_port = port or DEFAULT_BACKEND_PORT
        self.project_root = PROJECT_ROOT

        self.ollama = OllamaManager(
            ollama_url=DEFAULT_OLLAMA_URL,
            auto_start=not no_ollama,
            auto_pull=True,
        )
        self.credentials = CredentialManager(str(self.project_root))

        self._backend_process: Optional[subprocess.Popen] = None
        self._ui_process: Optional[subprocess.Popen] = None
        self._running = False

    # ─── Startup Sequence ──────────────────────────────────────────────

    def start(self):
        """Run the full startup sequence."""
        self._setup_logging()
        self._print_banner()

        logger.info("=" * 60)
        logger.info("SuperNEXUS v2.0 - Starting...")
        logger.info("=" * 60)

        # Step 1: Security check
        self._step_security_check()

        # Step 2: Ollama
        if not self.no_ollama:
            self._step_ollama()

        # Step 3: Backend
        self._step_backend()

        # Step 4: UI
        if not self.no_ui:
            self._step_ui()

        # Step 5: Health checks
        self._step_health_checks()

        # Step 6: Open browser
        if not self.no_ui:
            self._open_browser()

        self._running = True
        self._wait_for_exit()

    def _setup_logging(self):
        """Configure logging."""
        log_level = os.environ.get("NEXUS_LOG_LEVEL", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )

    def _print_banner(self):
        """Print startup banner."""
        print("""
╔══════════════════════════════════════════════════════╗
║                                                      ║
║   SuperNEXUS v2.0 - Sovereign Local AI Agent         ║
║   Brain + Tools Architecture                         ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
""")

    # ─── Step 1: Security Check ────────────────────────────────────────

    def _step_security_check(self):
        """Run credential security audit."""
        logger.info("[1/5] Security check...")
        result = self.credentials.run_doctor_check()
        if result["status"] == "FAIL":
            for issue in result["issues"]:
                if issue.startswith("CRITICAL"):
                    logger.warning(f"SECURITY: {issue}")
        else:
            logger.info("  Security check: PASS")

    # ─── Step 2: Ollama ────────────────────────────────────────────────

    def _step_ollama(self):
        """Ensure Ollama is running with required models."""
        logger.info("[2/5] Ollama...")

        if self.ollama.is_running():
            logger.info("  Ollama: Already running")
        elif self.ollama.start():
            logger.info("  Ollama: Started successfully")
        else:
            logger.warning("  Ollama: Could not start (will use fallback providers)")

        # Check required models
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            status = loop.run_until_complete(self.ollama.get_full_status())
            loop.close()

            missing = status.get("missing_required", [])
            if missing:
                logger.info(f"  Missing models: {', '.join(missing)}")
                logger.info("  Models will be pulled on first use")
            else:
                logger.info(f"  Models: {len(status.get('installed_models', []))} installed")
        except Exception as e:
            logger.warning(f"  Model check failed: {e}")

    # ─── Step 3: Backend ───────────────────────────────────────────────

    def _step_backend(self):
        """Start the backend server."""
        logger.info(f"[3/5] Backend (port {self.backend_port})...")

        env = os.environ.copy()
        env["NEXUS_BACKEND_PORT"] = str(self.backend_port)
        env["PYTHONUNBUFFERED"] = "1"

        server_script = self.project_root / "src" / "api" / "server.py"

        try:
            self._backend_process = subprocess.Popen(
                [sys.executable, str(server_script)],
                env=env,
                cwd=str(self.project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
            )
            logger.info(f"  Backend started (PID: {self._backend_process.pid})")

            # Wait for backend to be ready (60s for full module init)
            import httpx
            for i in range(60):
                time.sleep(1)
                try:
                    resp = httpx.get(f"http://localhost:{self.backend_port}/api/status", timeout=3.0)
                    if resp.status_code == 200:
                        logger.info("  Backend: Ready")
                        return
                except Exception:
                    continue

            logger.warning("  Backend: Did not become ready within 60 seconds")

        except Exception as e:
            logger.error(f"  Backend: Failed to start - {e}")

    # ─── Step 4: UI ────────────────────────────────────────────────────

    def _step_ui(self):
        """Start the UI dev server or open pre-built SPA."""
        logger.info(f"[4/5] UI (port {DEFAULT_UI_PORT})...")

        # Check if we have a built SPA
        dist_index = self.project_root / "ui" / "dist" / "index.html"
        if dist_index.exists():
            logger.info("  UI: Pre-built SPA available (served by backend)")
            return

        # Check for Vite dev server
        vite_config = self.project_root / "ui" / "vite.config.ts"
        if not vite_config.exists():
            logger.info("  UI: No Vite config found, skipping")
            return

        # Start Vite dev server
        try:
            self._ui_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", str(DEFAULT_UI_PORT)],
                cwd=str(self.project_root / "ui"),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
            )
            logger.info(f"  UI dev server started (PID: {self._ui_process.pid})")

            # Wait for UI to be ready
            import httpx
            for i in range(20):
                time.sleep(1)
                try:
                    resp = httpx.get(f"http://localhost:{DEFAULT_UI_PORT}", timeout=3.0)
                    if resp.status_code == 200:
                        logger.info("  UI: Ready")
                        return
                except Exception:
                    continue

            logger.warning("  UI: Did not become ready within 20 seconds")

        except Exception as e:
            logger.warning(f"  UI: Could not start dev server - {e}")
            logger.info("  UI: Try 'cd ui && npm run dev' manually")

    # ─── Step 5: Health Checks ─────────────────────────────────────────

    def _step_health_checks(self):
        """Verify all services are running."""
        logger.info("[5/5] Health checks...")

        import httpx
        services = {
            "Backend": f"http://localhost:{self.backend_port}/api/status",
            "Ollama": f"{DEFAULT_OLLAMA_URL}/api/tags",
        }

        all_ok = True
        for name, url in services.items():
            try:
                resp = httpx.get(url, timeout=5.0)
                status = "OK" if resp.status_code == 200 else f"HTTP {resp.status_code}"
                logger.info(f"  {name}: {status}")
                if resp.status_code != 200:
                    all_ok = False
            except Exception as e:
                logger.warning(f"  {name}: UNAVAILABLE ({e})")
                all_ok = False

        if all_ok:
            logger.info("  All services healthy")
        else:
            logger.warning("  Some services are not healthy")

    # ─── Browser ───────────────────────────────────────────────────────

    def _open_browser(self):
        """Open the UI in the default browser."""
        # Try UI dev server first, then backend
        url = f"http://localhost:{DEFAULT_UI_PORT}"
        try:
            import httpx
            resp = httpx.get(url, timeout=2.0)
            if resp.status_code == 200:
                logger.info(f"Opening UI: {url}")
                webbrowser.open(url)
                return
        except Exception:
            pass

        # Fallback to backend-served SPA
        url = f"http://localhost:{self.backend_port}/ui/"
        logger.info(f"Opening UI (backend): {url}")
        webbrowser.open(url)

    # ─── Shutdown ──────────────────────────────────────────────────────

    def _wait_for_exit(self):
        """Wait for Ctrl+C or termination signal."""
        def handler(sig, frame):
            logger.info("Shutdown signal received")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

        logger.info("SuperNEXUS is running. Press Ctrl+C to stop.")

        try:
            while self._running:
                time.sleep(1)
                # Check if backend is still running
                if self._backend_process and self._backend_process.poll() is not None:
                    logger.warning("Backend process exited unexpectedly")
                    self.stop()
                    break
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Graceful shutdown of all services."""
        logger.info("Shutting down SuperNEXUS...")
        self._running = False

        if self._ui_process:
            logger.info("Stopping UI...")
            try:
                self._ui_process.terminate()
                self._ui_process.wait(timeout=5)
            except Exception:
                self._ui_process.kill()

        if self._backend_process:
            logger.info("Stopping backend...")
            try:
                self._backend_process.terminate()
                self._backend_process.wait(timeout=10)
            except Exception:
                self._backend_process.kill()

        if not self.no_ollama:
            self.ollama.stop()

        logger.info("SuperNEXUS shut down complete")


def main():
    parser = argparse.ArgumentParser(description="SuperNEXUS v2.0 Launcher")
    parser.add_argument("--no-ui", action="store_true", help="Start without UI")
    parser.add_argument("--no-ollama", action="store_true", help="Don't manage Ollama")
    parser.add_argument("--port", type=int, default=None, help="Backend port (default: 9000)")
    parser.add_argument("--doctor", action="store_true", help="Run security doctor check and exit")
    parser.add_argument("--status", action="store_true", help="Show system status and exit")
    args = parser.parse_args()

    if args.doctor:
        creds = CredentialManager()
        result = creds.run_doctor_check()
        print(f"\nSecurity Status: {result['status']}")
        for issue in result["issues"]:
            print(f"  - {issue}")
        print()
        return

    if args.status:
        ollama = OllamaManager()
        print(f"\nOllama: {'Running' if ollama.is_running() else 'Not running'}")
        print(f"Installed: {ollama.is_installed()}")
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            models = loop.run_until_complete(ollama.list_models())
            loop.close()
            print(f"Models: {', '.join(models) if models else 'None'}")
        except Exception:
            pass
        print()
        return

    launcher = NexusLauncher(
        no_ui=args.no_ui,
        no_ollama=args.no_ollama,
        port=args.port,
    )
    launcher.start()


if __name__ == "__main__":
    main()
