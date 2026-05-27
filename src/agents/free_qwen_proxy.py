"""
FreeQwenApi - Proxy HTTP para acceso ilimitado a qwen3-coder-plus

Escucha en puerto 3264 y redirige peticiones OpenAI-compatible
a la API gratuita de Qwen (dashscope/compatible endpoint).

Uso:
    python free_qwen_proxy.py

Endpoints:
    POST /v1/chat/completions - Compatible con OpenAI SDK
    GET  /health - Health check
"""

import json
import logging
import httpx
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("free-qwen-proxy")

# Configuracion
LISTEN_PORT = 3264
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
QWEN_MODEL = "qwen3-coder-plus"
# API key gratuita de Qwen (si existe en el entorno)
import os
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "sk-free-qwen-proxy")


class QwenProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json_response(200, {"status": "ok", "model": QWEN_MODEL, "port": LISTEN_PORT})
        else:
            self._json_response(404, {"error": "Not found"})

    def do_POST(self):
        if self.path in ("/v1/chat/completions", "/chat/completions"):
            self._handle_chat_completion()
        else:
            self._json_response(404, {"error": "Not found"})

    def _handle_chat_completion(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            request_data = json.loads(body)

            # Asegurar modelo correcto
            request_data["model"] = QWEN_MODEL

            # Forward a Qwen API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {QWEN_API_KEY}",
            }

            with httpx.Client(timeout=120) as client:
                response = client.post(QWEN_API_URL, json=request_data, headers=headers)

            if response.status_code == 200:
                self._json_response(200, response.json())
            else:
                logger.error(f"Qwen API error: {response.status_code} - {response.text}")
                self._json_response(response.status_code, {
                    "error": f"Qwen API returned {response.status_code}",
                    "detail": response.text[:500],
                })
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            self._json_response(502, {"error": f"Upstream request failed: {str(e)}"})
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            self._json_response(500, {"error": str(e)})

    def _json_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")


def main():
    server = HTTPServer(("127.0.0.1", LISTEN_PORT), QwenProxyHandler)
    logger.info(f"FreeQwenApi proxy listening on http://127.0.0.1:{LISTEN_PORT}")
    logger.info(f"Model: {QWEN_MODEL}")
    logger.info(f"Upstream: {QWEN_API_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
