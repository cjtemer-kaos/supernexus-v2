import os
import wave
import json
import io
import tempfile
import threading
import numpy as np
from pathlib import Path

VOICE_MODELS_DIR = Path(__file__).parent.parent.parent / "voice_models" / "piper"

_engine = None
_lock = threading.Lock()


class VoiceEngine:
    def __init__(self):
        self.available = False
        self.model = None
        self.voice_name = "es_MX-claude-high"
        self.model_path = None
        self.config_path = None
        self.sample_rate = 22050
        self._init_engine()

    def _init_engine(self):
        try:
            from piper import PiperVoice
            voices = self.get_voices()
            if not voices:
                return
            quality_order = {"high": 0, "medium": 1, "low": 2, "unknown": 3}
            best = min(voices, key=lambda v: quality_order.get(v["quality"], 3))
            self.voice_name = best["name"]
            self.model_path = str(VOICE_MODELS_DIR / f"{self.voice_name}.onnx")
            self.config_path = str(VOICE_MODELS_DIR / f"{self.voice_name}.onnx.json")
            self.model = PiperVoice.load(self.model_path, config_path=self.config_path)
            with open(self.config_path, encoding="utf-8") as f:
                cfg = json.load(f)
            self.sample_rate = cfg.get("audio", {}).get("sample_rate", 22050)
            self.available = True
        except Exception:
            self.available = False

    def get_voices(self):
        voices = []
        if not VOICE_MODELS_DIR.exists():
            return voices
        for f in sorted(VOICE_MODELS_DIR.glob("*.onnx")):
            name = f.stem
            cfg_f = f.with_suffix(".onnx.json")
            quality = "unknown"
            if cfg_f.exists():
                try:
                    data = json.loads(cfg_f.read_text(encoding="utf-8"))
                    quality = data.get("audio", {}).get("quality", "unknown")
                except Exception:
                    pass
            voices.append({"name": name, "quality": quality})
        return voices

    def set_voice(self, name):
        from piper import PiperVoice
        onnx = VOICE_MODELS_DIR / f"{name}.onnx"
        cfg = VOICE_MODELS_DIR / f"{name}.onnx.json"
        if onnx.exists() and cfg.exists():
            self.model_path = str(onnx)
            self.config_path = str(cfg)
            self.voice_name = name
            self.model = PiperVoice.load(self.model_path, config_path=self.config_path)
            with open(self.config_path, encoding="utf-8") as f:
                data = json.load(f)
            self.sample_rate = data.get("audio", {}).get("sample_rate", 22050)
            return True
        return False

    def synthesize(self, text):
        if not self.available or not self.model:
            return None
        chunks = []
        for chunk in self.model.synthesize(text):
            chunks.append(chunk)
        if not chunks:
            return None
        return chunks

    def speak(self, text, out_path=None):
        chunks = self.synthesize(text)
        if not chunks:
            return None
        if out_path is None:
            out_path = os.path.join(tempfile.gettempdir(), f"nexus_voice_{abs(hash(text)) % 100000}.wav")
        with wave.open(out_path, "w") as wav:
            wav.setnchannels(chunks[0].sample_channels)
            wav.setsampwidth(chunks[0].sample_width)
            wav.setframerate(chunks[0].sample_rate)
            for chunk in chunks:
                wav.writeframes(chunk.audio_int16_bytes)
        return out_path

    def speak_bytes(self, text):
        chunks = self.synthesize(text)
        if not chunks:
            return None
        buf = io.BytesIO()
        with wave.open(buf, "w") as wav:
            wav.setnchannels(chunks[0].sample_channels)
            wav.setsampwidth(chunks[0].sample_width)
            wav.setframerate(chunks[0].sample_rate)
            for chunk in chunks:
                wav.writeframes(chunk.audio_int16_bytes)
        return buf.getvalue()


def get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = VoiceEngine()
    return _engine


def speak(text, out_path=None):
    engine = get_engine()
    if engine.available:
        return engine.speak(text, out_path)
    return None
