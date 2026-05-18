"""
Ollama Integration - LLM local para SuperNEXUS v2.0

Conexion a Ollama para generación de texto, embeddings, y routing semantico.
Sin secrets - usa Ollama local por defecto.
"""

import json
import logging
from typing import AsyncIterator, Dict, List, Optional
from datetime import datetime

import httpx

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Cliente para Ollama API local.
    Soporta chat, embeddings, y listing de modelos.
    """

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)

    async def _resolve_model(self, model: str) -> str:
        """
        Resuelve el modelo solicitado a uno disponible localmente en Ollama.
        Evita fallos si se pide un tag inexistente (ej: deepseek-r1:8b en lugar de deepseek-r1:7b).
        """
        try:
            models = await self.list_models()
            if not models:
                return model
            
            available_names = [m.get("name", "") for m in models if m.get("name")]
            
            # 1. Coincidencia exacta
            if model in available_names:
                return model
                
            # 2. Coincidencia sin tag o con otro tag (ej: deepseek-r1:8b -> deepseek-r1:7b)
            base_requested = model.split(":")[0]
            for av in available_names:
                base_av = av.split(":")[0]
                if base_requested == base_av:
                    logger.warning(f"OllamaClient: Redireccionando modelo inexistente '{model}' -> '{av}'")
                    return av
            
            # 3. Coincidencia parcial difusa (ej: deepseek -> deepseek-r1:7b)
            for av in available_names:
                if base_requested in av or av in base_requested:
                    logger.warning(f"OllamaClient: Coincidencia difusa de modelo '{model}' -> '{av}'")
                    return av
                    
            # 4. Fallback al primer modelo no-embedding disponible (evita usar nomene/embed para chat)
            non_embed_models = [m for m in available_names if "embed" not in m.lower() and "nomic" not in m.lower()]
            if non_embed_models:
                logger.warning(f"OllamaClient: Ninguna coincidencia para '{model}'. Usando fallback: '{non_embed_models[0]}'")
                return non_embed_models[0]
                
            # 5. Fallback definitivo si no hay nada más
            return available_names[0]
        except Exception as e:
            logger.error(f"Error resolviendo modelo Ollama '{model}': {e}")
            return model

    async def chat(
        self,
        model: str,
        messages: List,
        stream: bool = False,
        options: Optional[Dict] = None,
    ) -> Dict:
        """
        Chat con modelo de Ollama.
        messages: [{"role": "user", "content": "..."}, ...]
        """
        model = await self._resolve_model(model)
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if options:
            payload["options"] = options

        r = await self.client.post(f"{self.base_url}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()

    async def chat_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict] = None,
    ) -> AsyncIterator[str]:
        """Chat con streaming de respuesta"""
        model = await self._resolve_model(model)
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        if options:
            payload["options"] = options

        async with self.client.stream(
            "POST", f"{self.base_url}/api/chat", json=payload
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line:
                    data = json.loads(line)
                    if data.get("done"):
                        break
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        stream: bool = False,
        options: Optional[Dict] = None,
    ) -> Dict:
        """Generacion directa (sin chat history)"""
        model = await self._resolve_model(model)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        r = await self.client.post(f"{self.base_url}/api/generate", json=payload)
        r.raise_for_status()
        return r.json()

    async def embed(self, model: str, input: List[str]) -> List[List[float]]:
        """Genera embeddings para RAG"""
        model = await self._resolve_model(model)
        payload = {"model": model, "input": input}
        r = await self.client.post(f"{self.base_url}/api/embed", json=payload)
        r.raise_for_status()
        return r.json().get("embeddings", [])

    async def list_models(self) -> List[Dict]:
        """Lista modelos disponibles"""
        r = await self.client.get(f"{self.base_url}/api/tags")
        r.raise_for_status()
        return r.json().get("models", [])

    async def auto_discover(self) -> str:
        """
        Dynamically discover active Ollama instance on local machine or standard network ports.
        Checks OLLAMA_HOST environment variable, standard port 11434, and alternative ports.
        """
        import os
        env_host = os.getenv("OLLAMA_HOST")
        if env_host:
            if not env_host.startswith("http"):
                env_host = f"http://{env_host}"
            self.base_url = env_host.rstrip("/")
            try:
                r = await self.client.get(f"{self.base_url}/api/tags", timeout=1.0)
                if r.status_code == 200:
                    logger.info(f"Ollama auto-discovered via OLLAMA_HOST: {self.base_url}")
                    return self.base_url
            except Exception:
                pass

        standard_ports = [11434, 11435, 18789, 8000]
        for port in standard_ports:
            test_url = f"http://localhost:{port}"
            try:
                r = await self.client.get(f"{test_url}/api/tags", timeout=1.0)
                if r.status_code == 200:
                    self.base_url = test_url
                    logger.info(f"Ollama auto-discovered on active port {port}: {self.base_url}")
                    return self.base_url
            except Exception:
                continue

        return self.base_url

    async def is_available(self) -> bool:
        """Verifica si Ollama esta disponible"""
        try:
            r = await self.client.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                return True
        except:
            pass

        # Try auto-discovery
        original_url = self.base_url
        discovered_url = await self.auto_discover()
        if discovered_url != original_url:
            try:
                r = await self.client.get(f"{self.base_url}/api/tags", timeout=5)
                return r.status_code == 200
            except:
                pass
        return False

    async def close(self):
        await self.client.aclose()



class LLMRouter:
    """
    Router de LLMs para SuperNEXUS.
    Selecciona modelo segun tipo de tarea.
    """

    DEFAULT_MODELS = {
        "default": "nemotron-3-nano:4b",
        "coding": "qwen2.5-coder:7b",
        "reasoning": "deepseek-r1:8b",
        "fast": "nemotron-3-nano:4b",
        "chat": "llama3.2:3b",
        "embedding": "nomic-embed-text",
    }

    def __init__(self, ollama: Optional[OllamaClient] = None, models: Optional[Dict] = None):
        self.ollama = ollama or OllamaClient()
        self.models = models or self.DEFAULT_MODELS

    def get_model_for_task(self, task: str) -> str:
        """Selecciona modelo segun tipo de tarea"""
        task_lower = task.lower()

        if any(k in task_lower for k in ["code", "program", "script", "debug", "fix"]):
            return self.models.get("coding", "qwen2.5-coder:7b")
        elif any(k in task_lower for k in ["think", "reason", "analyze", "plan", "design"]):
            return self.models.get("reasoning", "deepseek-r1:7b")
        elif any(k in task_lower for k in ["quick", "simple", "fast", "summary"]):
            return self.models.get("fast", "nemotron-3-nano:4b")
        else:
            return self.models.get("default", "llama3.2")

    async def classify_intent(self, query: str) -> Dict:
        """Clasifica intencion del usuario usando LLM"""
        prompt = f"""Classify this query into one category: code, research, debug, creative, devops, security, general.
Query: {query}
Return only the category name."""

        response = await self.ollama.generate(
            model=self.models.get("fast", "nemotron-3-nano:4b"),
            prompt=prompt,
        )
        category = response.get("response", "general").strip().lower()
        return {"category": category, "confidence": 0.8}

    async def route_task(self, task: str) -> Dict:
        """Rutea tarea al modelo y gema apropiado"""
        intent = await self.classify_intent(task)
        model = self.get_model_for_task(task)

        gem_mapping = {
            "code": "coder",
            "research": "scholar",
            "debug": "debugger",
            "creative": "creative",
            "devops": "devops",
            "security": "security",
            "general": "director",
        }

        return {
            "model": model,
            "gem": gem_mapping.get(intent["category"], "director"),
            "intent": intent,
        }

    async def generate_response(
        self,
        task: str,
        context: str = "",
        stream: bool = False,
    ) -> Dict:
        """Genera respuesta completa para una tarea"""
        routing = await self.route_task(task)
        model = routing["model"]

        system_prompt = f"""You are SuperNEXUS v2.0, an AI organism.
You are acting as the {routing['gem']} gem.
Be concise, helpful, and accurate.
If you don't know something, say so."""

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})

        messages.append({"role": "user", "content": task})

        if stream:
            return {"stream": True, "model": model, "routing": routing}
        else:
            response = await self.ollama.chat(model=model, messages=messages)
            return {
                "reply": response.get("message", {}).get("content", ""),
                "model": model,
                "routing": routing,
                "done": response.get("done", False),
            }
