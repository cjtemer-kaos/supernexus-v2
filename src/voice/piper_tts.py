"""
Piper TTS Integration - Motor de voz local 100% offline para SuperNEXUS v2
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_MODEL_DIR = Path(__file__).parent.parent.parent / "voice_models" / "piper"

PIPER_VOICES_ES = {
    "davefx-medium": {
        "name": "Dave (España)",
        "gender": "Male",
        "quality": "medium",
        "onnx": "es_ES-davefx-medium.onnx",
        "config": "es_ES-davefx-medium.onnx.json",
    },
    "sharvard-medium": {
        "name": "Sharvard (España)",
        "gender": "Male",
        "quality": "medium",
        "onnx": "es_ES-sharvard-medium.onnx",
        "config": "es_ES-sharvard-medium.onnx.json",
    },
    "ald-medium": {
        "name": "Ald (México)",
        "gender": "Male",
        "quality": "medium",
        "onnx": "es_MX-ald-medium.onnx",
        "config": "es_MX-ald-medium.onnx.json",
    },
    "claude-high": {
        "name": "Claude (México HQ)",
        "gender": "Male",
        "quality": "high",
        "onnx": "es_MX-claude-high.onnx",
        "config": "es_MX-claude-high.onnx.json",
    },
    "carlfm-xlow": {
        "name": "Carl FM (España)",
        "gender": "Male",
        "quality": "x_low",
        "onnx": "es_ES-carlfm-x_low.onnx",
        "config": "es_ES-carlfm-x_low.onnx.json",
    },
}

# HuggingFace auto-download paths (repo: rhasspy/piper-voices)
PIPER_HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
PIPER_HF_PATHS = {
    "davefx-medium": "es/es_ES/davefx/medium",
    "sharvard-medium": "es/es_ES/sharvard/medium",
    "ald-medium": "es/es_MX/ald/medium",
    "claude-high": "es/es_MX/claude/high",
    "carlfm-xlow": "es/es_ES/carlfm/x_low",
}


class PiperTTS:
    """Motor TTS local usando Piper - 100% offline"""

    def __init__(self, model_dir: Optional[Path] = None, voice: str = "davefx-medium"):
        self.model_dir = model_dir or DEFAULT_MODEL_DIR
        self.voice = voice
        self._voice = None
        self._loaded = False

    def _auto_download(self, voice_key: str, voice_info: dict) -> bool:
        """Descarga voz de HuggingFace si no existe localmente"""
        hf_path = PIPER_HF_PATHS.get(voice_key)
        if not hf_path:
            return False
        self.model_dir.mkdir(parents=True, exist_ok=True)
        for fname in [voice_info["onnx"], voice_info["config"]]:
            dest = self.model_dir / fname
            if dest.exists():
                continue
            url = f"{PIPER_HF_BASE}/{hf_path}/{fname}?download=true"
            logger.info(f"Descargando voz Piper: {fname}...")
            try:
                import urllib.request
                urllib.request.urlretrieve(url, str(dest))
                logger.info(f"Descargado: {fname}")
            except Exception as e:
                logger.error(f"Error descargando {fname}: {e}")
                return False
        return True

    def load(self, voice: Optional[str] = None) -> bool:
        """Carga el modelo de voz Piper"""
        voice_key = voice or self.voice
        voice_info = PIPER_VOICES_ES.get(voice_key)

        if not voice_info:
            logger.error(f"Voz no encontrada: {voice_key}")
            return False

        onnx_path = self.model_dir / voice_info["onnx"]
        config_path = self.model_dir / voice_info["config"]

        # Auto-download if missing
        if not onnx_path.exists() or not config_path.exists():
            if not self._auto_download(voice_key, voice_info):
                logger.error(f"Modelo no disponible y no se pudo descargar: {voice_key}")
                return False

        try:
            from piper import PiperVoice
            self._voice = PiperVoice.load(str(onnx_path), config_path=str(config_path))
            self._loaded = True
            self.voice = voice_key
            logger.info(f"Piper TTS cargado: {voice_info['name']}")
            return True
        except Exception as e:
            logger.error(f"Error cargando Piper: {e}")
            return False

    def synthesize(self, text: str) -> bytes:
        """Sintetiza texto a audio WAV bytes"""
        if not self._loaded:
            if not self.load():
                raise RuntimeError("Piper TTS no cargado")

        import io
        import wave

        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, 'wb') as wav_file:
            self._voice.synthesize_wav(text, wav_file)
        
        audio_buffer.seek(0)
        return audio_buffer.getvalue()

    async def synthesize_async(self, text: str) -> bytes:
        """Sintetiza texto a audio WAV bytes (async)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.synthesize, text)

    async def speak(self, text: str):
        """Reproduce audio directamente"""
        if not self._loaded:
            if not self.load():
                return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._speak_sync, text)

    def _speak_sync(self, text: str):
        """Sintetiza y reproduce usando sounddevice"""
        import io
        import wave
        import sounddevice as sd
        import numpy as np

        # Generar WAV
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, 'wb') as wav_file:
            self._voice.synthesize_wav(text, wav_file)
        
        audio_buffer.seek(0)
        
        # Leer WAV
        with wave.open(audio_buffer, 'rb') as wf:
            sample_rate = wf.getframerate()
            n_frames = wf.getnframes()
            audio_data = wf.readframes(n_frames)
        
        # Convertir a numpy array float32 [-1, 1]
        audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        sd.play(audio_np, samplerate=sample_rate)
        sd.wait()

    async def save_to_file(self, text: str, output_path: str):
        """Guarda audio sintetizado en archivo WAV"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._save_sync, text, output_path)

    def _save_sync(self, text: str, output_path: str):
        """Sintetiza y guarda en archivo"""
        audio_bytes = self.synthesize(text)
        with open(output_path, 'wb') as f:
            f.write(audio_bytes)

    def get_available_voices(self) -> List[Dict]:
        """Lista voces disponibles"""
        voices = []
        for key, info in PIPER_VOICES_ES.items():
            onnx_path = self.model_dir / info["onnx"]
            voices.append({
                "id": key,
                "name": info["name"],
                "gender": info["gender"],
                "quality": info["quality"],
                "installed": onnx_path.exists(),
                "local": True,
            })
        return voices


piper_tts = PiperTTS()
