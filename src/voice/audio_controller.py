"""
Audio Controller - Async para SuperNEXUS v2
Captura de microfono + Whisper STT (faster-whisper / openai-whisper / Ollama fallback)
"""

import asyncio
import base64
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

OLLAMA_SERVER = "http://localhost:11434"
WHISPER_MODEL = "base"


class AudioController:
    """Control de audio async con Whisper STT"""

    def __init__(self, model: str = WHISPER_MODEL):
        self.model = model
        self.audio = None
        self.model_loaded = False
        self.whisper_model = None
        self._audio_ready = False
        self.CHUNK = 1024
        self.CHANNELS = 1
        self.RATE = 16000
        self.input_device = 0

    async def initialize(self) -> bool:
        """Inicializa captura de audio y carga modelo"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            default_input = p.get_default_input_device_info()
            self.input_device = default_input['index']
            self.audio = p
            self._audio_ready = True
            logger.info(f"Microfono listo: {default_input['name']}")
        except ImportError:
            logger.warning("PyAudio no instalado")
            self._audio_ready = False
        except Exception as e:
            logger.error(f"Audio init error: {e}")
            self._audio_ready = False

        await self.load_model()
        return self._audio_ready

    async def load_model(self) -> bool:
        """Carga modelo Whisper"""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Cargando faster-whisper ({self.model})...")
            self.whisper_model = WhisperModel(self.model, device="cpu", compute_type="int8")
            self.model_loaded = True
            logger.info("Modelo cargado (faster-whisper)")
            return True
        except ImportError:
            pass

        try:
            import whisper
            logger.info(f"Cargando whisper ({self.model})...")
            loop = asyncio.get_event_loop()
            self.whisper_model = await loop.run_in_executor(None, whisper.load_model, self.model)
            self.model_loaded = True
            logger.info("Modelo cargado (whisper)")
            return True
        except ImportError:
            pass

        logger.warning("No hay whisper local. Usando Ollama como fallback.")
        self.model_loaded = False
        return False

    async def _capture_audio(self, duration: float = 3.0) -> bytes:
        """Captura audio del microfono"""
        if not self._audio_ready or not self.audio:
            return b""

        frames = []
        chunks = int(self.RATE / self.CHUNK * duration)

        try:
            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(
                None,
                lambda: self.audio.open(
                    format=self.audio.get_format_from_width(2),
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    input_device_index=self.input_device,
                    frames_per_buffer=self.CHUNK,
                )
            )

            for _ in range(chunks):
                data = await loop.run_in_executor(None, stream.read, self.CHUNK, False)
                frames.append(data)

            await loop.run_in_executor(None, stream.stop_stream)
            await loop.run_in_executor(None, stream.close)
            return b''.join(frames)
        except Exception as e:
            logger.error(f"Error capturando audio: {e}")
            return b""

    def _recognize_faster_whisper(self, audio_bytes: bytes) -> Tuple[str, str]:
        import subprocess
        """Transcribe con faster-whisper, convierte webm a wav si es necesario"""
        temp_path = None
        wav_path = None
        try:
            # Detectar formato por magic bytes
            is_webm = audio_bytes[:4] == b'\x1a\x45\xdf\xa3'
            is_mp3 = audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb'
            
            if is_webm or is_mp3:
                # Convertir a WAV para whisper
                wav_path = tempfile.mktemp(suffix=".wav")
                with tempfile.NamedTemporaryFile(suffix=".webm" if is_webm else ".mp3", delete=False) as f:
                    f.write(audio_bytes)
                    temp_path = f.name
                
                subprocess.run([
                    "ffmpeg", "-y", "-i", temp_path,
                    "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                    wav_path
                ], check=True, capture_output=True, timeout=30)
                
                with open(wav_path, "rb") as f:
                    wav_bytes = f.read()
            else:
                wav_bytes = audio_bytes
            
            # Escribir WAV temporal para whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(wav_bytes)
                whisper_path = f.name
            
            segments, info = self.whisper_model.transcribe(whisper_path, language="es")
            text = " ".join([s.text for s in segments])
            return text.strip(), info.language or "es"
        finally:
            for p in [temp_path, wav_path]:
                if p:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

    def _recognize_whisper(self, audio_bytes: bytes) -> Tuple[str, str]:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        try:
            result = self.whisper_model.transcribe(temp_path, language="es")
            return result["text"].strip(), "es"
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    async def _recognize_ollama(self, audio_bytes: bytes) -> Tuple[str, str]:
        import httpx
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode()
            prompt = "Analiza este audio y extrae el texto spoken. Responde SOLO con el texto detectado en espanol, o 'sin audio' si no hay voz clara."
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(f"{OLLAMA_SERVER}/api/generate", json={
                    "model": "whisper",
                    "prompt": prompt,
                    "images": [audio_b64] if audio_b64 else [],
                    "stream": False,
                })
                if r.status_code == 200:
                    return r.json().get("response", "sin audio"), "es"
        except Exception as e:
            logger.error(f"Ollama fallback error: {e}")
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        return "sin audio", "es"

    async def recognize(self, audio_bytes: bytes) -> Tuple[str, str]:
        """Reconoce texto del audio (webm, wav, mp3, etc)"""
        if not audio_bytes:
            return "sin audio", "es"

        if self.model_loaded and self.whisper_model:
            try:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, self._recognize_faster_whisper, audio_bytes
                )
            except Exception as e:
                logger.error(f"faster-whisper error: {e}")

        return await self._recognize_ollama(audio_bytes)

    async def listen_for_command(self, timeout: float = 3.0) -> Tuple[str, str]:
        """Escucha comando de voz"""
        logger.info(f"Escuchando... ({timeout}s)")
        audio_bytes = await self._capture_audio(duration=timeout)
        if not audio_bytes:
            return "", "es"
        text, lang = await self.recognize(audio_bytes)
        return text.strip(), lang

    async def listen_continuous(self, callback, stop_event: threading.Event):
        """Escucha continua con callback"""
        logger.info("Modo continuo iniciado")
        while not stop_event.is_set():
            audio_bytes = await self._capture_audio(duration=2.0)
            if audio_bytes:
                text, lang = await self.recognize(audio_bytes)
                if text and text != "sin audio":
                    if asyncio.iscoroutinefunction(callback):
                        await callback(text, lang)
                    else:
                        callback(text, lang)

    async def transcribe_file(self, file_path: str) -> dict:
        """Transcribe archivo de audio"""
        if not os.path.exists(file_path):
            return {"error": "Archivo no encontrado"}

        try:
            import httpx
            with open(file_path, "rb") as f:
                audio_data = f.read()
            audio_b64 = base64.b64encode(audio_data).decode()
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(f"{OLLAMA_SERVER}/api/generate", json={
                    "model": "llama3.2",
                    "prompt": "Extrae el texto hablado de este audio.",
                    "images": [audio_b64],
                    "stream": False,
                })
                if r.status_code == 200:
                    return {"text": r.json().get("response", ""), "language": "es"}
        except Exception as e:
            return {"error": str(e)}
        return {"error": "Transcripcion fallida"}

    def close(self):
        if self.audio:
            self.audio.terminate()
            self.audio = None
        logger.info("AudioController cerrado")
