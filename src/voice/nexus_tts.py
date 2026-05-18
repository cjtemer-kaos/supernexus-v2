"""
Nexus TTS - Async multi-motor para SuperNEXUS v2
Soporta pyttsx3 (local) y edge_tts (cloud, mas natural)
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

VOICES_ES = {
    "es-MX-Dalia": {"name": "Dalia (Mexico)", "gender": "Female", "short": "es-MX-DaliaNeural"},
    "es-MX-Jorge": {"name": "Jorge (Mexico)", "gender": "Male", "short": "es-MX-JorgeNeural"},
    "es-AR-Elena": {"name": "Elena (Argentina)", "gender": "Female", "short": "es-AR-ElenaNeural"},
    "es-AR-Tomas": {"name": "Tomas (Argentina)", "gender": "Male", "short": "es-AR-TomasNeural"},
    "es-CO-Salome": {"name": "Salome (Colombia)", "gender": "Female", "short": "es-CO-SalomeNeural"},
    "es-CO-Gonzalo": {"name": "Gonzalo (Colombia)", "gender": "Male", "short": "es-CO-GonzaloNeural"},
    "es-ES-Ximena": {"name": "Ximena (Espana)", "gender": "Female", "short": "es-ES-XimenaNeural"},
    "es-CL-Catalina": {"name": "Catalina (Chile)", "gender": "Female", "short": "es-CL-CatalinaNeural"},
    "es-CL-Lorenzo": {"name": "Lorenzo (Chile)", "gender": "Male", "short": "es-CL-LorenzoNeural"},
}


class NexusTTS:
    """Motor de Text-to-Speech async"""

    def __init__(self, motor: str = "edge", voice: str = None):
        self.motor = motor
        self.voice = voice or "es-MX-Dalia"
        self.rate = 150
        self.volume = 1.0
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        if self.motor == "pyttsx3":
            try:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._engine.setProperty('rate', self.rate)
                self._engine.setProperty('volume', self.volume)
                logger.info("pyttsx3 engine initialized")
            except Exception as e:
                logger.error(f"pyttsx3 init error: {e}")
                self._engine = None

    def set_voice(self, voice_id: str):
        self.voice = voice_id
        if self.motor == "pyttsx3" and self._engine:
            try:
                voices = self._engine.getProperty('voices')
                for v in voices:
                    if voice_id in v.name:
                        self._engine.setProperty('voice', v.id)
                        break
            except Exception:
                pass

    def set_rate(self, rate: int):
        self.rate = rate
        if self._engine:
            self._engine.setProperty('rate', rate)

    def set_volume(self, volume: float):
        self.volume = volume
        if self._engine:
            self._engine.setProperty('volume', volume)

    async def speak(self, text: str):
        if self.motor == "edge":
            await self._speak_edge(text)
        else:
            await self._speak_pyttsx3(text)

    async def _speak_pyttsx3(self, text: str):
        if not self._engine:
            logger.warning("pyttsx3 engine no disponible")
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: (self._engine.say(text), self._engine.runAndWait()))

    async def _speak_edge(self, text: str):
        try:
            import edge_tts
            voice_info = VOICES_ES.get(self.voice, VOICES_ES["es-MX-Dalia"])
            communicate = edge_tts.Communicate(text, voice_info["short"])

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_file = f.name

            await communicate.save(temp_file)

            if os.name == 'nt':
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(
                        ["cmd", "/c", "start", "/min", "wmplayer", temp_file],
                        check=False, capture_output=True
                    )
                )
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: subprocess.run(["xdg-open", temp_file], check=False, capture_output=True)
                )

            await asyncio.sleep(1)
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        except ImportError:
            logger.error("edge_tts no disponible")
        except Exception as e:
            logger.error(f"edge_tts error: {e}")

    def get_voices_list(self) -> Dict:
        if self.motor == "edge":
            return VOICES_ES
        voices = {}
        if self._engine:
            for v in self._engine.getProperty('voices'):
                voices[v.id] = {"name": v.name, "gender": "Unknown"}
        return voices

    def close(self):
        if self._engine:
            self._engine.stop()


    async def speak_to_file(self, text: str, output_path: str):
        """Guarda TTS en archivo WAV para Wav2Lip"""
        if self.motor == "edge":
            await self._speak_edge_file(text, output_path)
        else:
            await self._speak_pyttsx3_file(text, output_path)

    async def _speak_pyttsx3_file(self, text: str, output_path: str):
        """pyttsx3 a archivo"""
        if not self._engine:
            raise RuntimeError("pyttsx3 no disponible")
        import wave
        import pyaudio
        # pyttsx3 no soporta export directo, usamos fallback edge
        await self._speak_edge_file(text, output_path)

    async def _speak_edge_file(self, text: str, output_path: str):
        """edge_tts a archivo WAV"""
        import edge_tts
        import subprocess
        voice_info = VOICES_ES.get(self.voice, VOICES_ES["es-MX-Dalia"])
        communicate = edge_tts.Communicate(text, voice_info["short"])
        await communicate.save(output_path.replace(".wav", ".mp3"))
        
        # Convertir MP3 a WAV para Wav2Lip
        subprocess.run([
            "ffmpeg", "-y", "-i", output_path.replace(".wav", ".mp3"),
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            output_path
        ], check=True, capture_output=True)
        
        # Limpiar MP3 temporal
        if os.path.exists(output_path.replace(".wav", ".mp3")):
            os.unlink(output_path.replace(".wav", ".mp3"))


async def speak_async(text: str, motor: str = "pyttsx3", voice: str = None):
    """Funcion helper async para TTS"""
    engine = NexusTTS(motor=motor, voice=voice)
    await engine.speak(text)
    engine.close()
