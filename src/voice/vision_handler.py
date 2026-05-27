"""
VisionHandler - Procesamiento de imagenes para SuperNEXUS

- Imagenes se codifican como base64 data URIs
- Formato de mensaje: ```image\n<path>\n```\ntexto
- Compatible con modelos vision de Ollama (qwen2.5vl, moondream, llava)
- Soporta screenshots, archivos de imagen, y clipboard paste

Integracion con NexusTrainer: las conversaciones con imagenes se recolectan
para entrenar modelos vision locales.
"""

import base64
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Extensiones soportadas
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
FILE_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | {'.pdf', '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json', '.yaml', '.xml', '.csv'}


class VisionHandler:
    """Maneja imagenes y archivos multimedia para SuperNEXUS"""

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.vision_models = [
            "qwen2.5vl:7b",
            "qwen2.5vl:3b",
            "qwen2.5vl:2b",
            "moondream:latest",
            "llava:7b",
            "llava:13b",
            "bakllava:latest",
            "llama3.2-vision:11b",
            "llama3.2-vision:90b",
        ]

    def encode_image_base64(self, file_path: str) -> str:
        """Codifica imagen a base64 data URI"""
        if file_path.startswith("http"):
            import httpx
            response = httpx.get(file_path)
            file_path = os.path.join(tempfile.gettempdir(), file_path.split("/")[-1])
            with open(file_path, "wb") as f:
                f.write(response.content)

        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.gif': 'image/gif',
            '.tiff': 'image/tiff',
        }
        mime_type = mime_types.get(ext, 'image/jpeg')

        with open(file_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        return f"data:{mime_type};base64,{encoded}"

    def decode_image_base64(self, data_uri: str) -> str:
        """Decodifica base64 data URI a archivo temporal"""
        if not data_uri.startswith("data:image/"):
            return data_uri  # Ya es un path

        header_end = data_uri.index(",")
        mime_type = data_uri[5:header_end]
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/gif": ".gif",
        }
        ext = ext_map.get(mime_type, ".jpg")
        raw_data = base64.b64decode(data_uri[header_end + 1:])

        saved_path = os.path.join(tempfile.gettempdir(), f"nexus_vision_{hash(data_uri[:30])}{ext}")
        with open(saved_path, "wb") as f:
            f.write(raw_data)
        return saved_path

    def extract_image_from_message(self, message: str) -> Tuple[Optional[str], str]:
        """Extrae imagen de mensaje"""
        # Formato: ```image\n<path_or_base64>\n```\ntexto
        if message.startswith("```image"):
            parts = message.split("\n", 2)
            if len(parts) >= 3:
                image_data = parts[1].strip()
                text = parts[2].strip()
                if text.startswith("```"):
                    text = text[3:].lstrip("\n")
                return image_data, text
        return None, message

    def extract_video_from_message(self, message: str) -> Tuple[Optional[str], str]:
        """Extrae video de mensaje"""
        if message.startswith("```video"):
            parts = message.split("\n", 2)
            if len(parts) >= 3:
                video_data = parts[1].strip()
                text = parts[2].strip()
                if text.startswith("```"):
                    text = text[3:].lstrip("\n")
                return video_data, text
        return None, message

    def extract_file_from_message(self, message: str) -> Tuple[Optional[str], str]:
        """Extrae archivo de mensaje"""
        if message.startswith("```file"):
            parts = message.split("\n", 2)
            if len(parts) >= 3:
                file_data = parts[1].strip()
                text = parts[2].strip()
                if text.startswith("```"):
                    text = text[3:].lstrip("\n")
                return file_data, text
        return None, message

    def format_message_with_image(self, image_path: str, text: str = "") -> str:
        """Formatea mensaje con imagen para el LLM"""
        return f"```image\n{image_path}\n```\n{text}"

    def format_message_with_file(self, file_path: str, text: str = "") -> str:
        """Formatea mensaje con archivo"""
        return f"```file\n{file_path}\n```\n{text}"

    def prepare_ollama_vision_request(self, message: str, model: str = "qwen2.5vl:7b") -> Dict:
        """Prepara request para Ollama con vision"""
        image_data, text = self.extract_image_from_message(message)

        payload = {
            "model": model,
            "prompt": text,
            "stream": False,
        }

        if image_data:
            # Si es un path, codificar a base64
            if not image_data.startswith("data:image/"):
                if os.path.exists(image_data):
                    image_data = self.encode_image_base64(image_data)
                else:
                    logger.warning(f"Imagen no encontrada: {image_data}")
                    return payload

            # Ollama espera "images" como lista de base64 strings (sin el data: prefix)
            if image_data.startswith("data:image/"):
                base64_data = image_data.split(",", 1)[1]
            else:
                base64_data = image_data

            payload["images"] = [base64_data]

        return payload

    def prepare_openai_vision_request(self, messages: List[Dict], model: str = "gpt-4-vision-preview") -> Dict:
        """Prepara request formato OpenAI con vision"""
        formatted_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            image_data, text = self.extract_image_from_message(content)

            if image_data:
                # Formato OpenAI multimodal
                if not image_data.startswith("data:image/"):
                    if os.path.exists(image_data):
                        image_data = self.encode_image_base64(image_data)

                content_parts = [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": image_data}},
                ]
                formatted_messages.append({"role": role, "content": content_parts})
            else:
                formatted_messages.append({"role": role, "content": content})

        return {"model": model, "messages": formatted_messages}

    def describe_image(self, image_path: str, prompt: str = "Describe esta imagen en detalle", model: str = "qwen2.5vl:7b") -> str:
        """Describe una imagen usando modelo vision local"""
        import httpx

        image_data = self.encode_image_base64(image_path)
        base64_data = image_data.split(",", 1)[1]

        payload = {
            "model": model,
            "prompt": prompt,
            "images": [base64_data],
            "stream": False,
        }

        try:
            response = httpx.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60.0,
            )
            if response.status_code == 200:
                return response.json().get("response", "No se pudo describir la imagen")
        except Exception as e:
            logger.error(f"Error describiendo imagen: {e}")

        return f"Error: {e}"

    def ocr_image(self, image_path: str) -> str:
        """Extrae texto de imagen (OCR)"""
        return self.describe_image(image_path, "Extrae todo el texto visible en esta imagen. Responde solo con el texto encontrado.")

    def analyze_code_screenshot(self, image_path: str) -> str:
        """Analiza screenshot de codigo"""
        return self.describe_image(image_path, "Analiza este screenshot de codigo. Identifica el lenguaje, la estructura, y cualquier error visible.")

    def get_available_vision_models(self) -> List[str]:
        """Lista modelos vision disponibles en Ollama"""
        import httpx

        try:
            response = httpx.get(f"{self.ollama_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [m["name"] for m in models if any(vm in m["name"] for vm in ["vl", "vision", "llava", "moondream", "bakllava"])]
        except Exception:
            pass

        return self.vision_models

    def is_vision_model(self, model_name: str) -> bool:
        """Verifica si un modelo soporta vision"""
        vision_keywords = ["vl", "vision", "llava", "moondream", "bakllava"]
        return any(kw in model_name.lower() for kw in vision_keywords)

    def process_multimodal_input(self, message: str, model: str = "auto") -> Dict:
        """Procesa input multimodal (texto + imagen/archivo)"""
        result = {
            "text": message,
            "images": [],
            "files": [],
            "has_multimodal": False,
        }

        # Extraer imagenes
        image_data, text = self.extract_image_from_message(message)
        if image_data:
            result["images"].append(image_data)
            result["text"] = text
            result["has_multimodal"] = True

        # Extraer archivos
        file_data, text = self.extract_file_from_message(text)
        if file_data:
            result["files"].append(file_data)
            result["text"] = text
            result["has_multimodal"] = True

        # Si no hay formato explicito, detectar por extension en el texto
        if not result["has_multimodal"]:
            for word in message.split():
                word = word.strip("()[]{}\"'")
                ext = Path(word).suffix.lower()
                if ext in IMAGE_EXTENSIONS and os.path.exists(word):
                    result["images"].append(word)
                    result["has_multimodal"] = True
                elif ext in FILE_EXTENSIONS and os.path.exists(word):
                    result["files"].append(word)
                    result["has_multimodal"] = True

        return result


# Singleton global
vision_handler = VisionHandler()
