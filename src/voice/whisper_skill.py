"""
Whisper Skill - Transcripción de audio para SuperNEXUS v2
Portado desde skills legacy (Zona Zero)
"""

import os
import tempfile
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class WhisperSkill:
    """
    Transcripción de audio usando Whisper
    Soporta múltiples modelos y formatos de audio
    """
    
    def __init__(self, model: str = "base"):
        self.name = "Whisper Transcription"
        self.version = "1.0"
        self.model = model
        self.models = ["tiny", "base", "small", "medium", "large"]
        self._model_loaded = False
        self._whisper_model = None
    
    def load_model(self) -> bool:
        """Carga el modelo Whisper"""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Cargando faster-whisper ({self.model})...")
            self._whisper_model = WhisperModel(self.model, device="cpu", compute_type="int8")
            self._model_loaded = True
            logger.info("Modelo cargado (faster-whisper)")
            return True
        except ImportError:
            pass
        
        try:
            import whisper
            logger.info(f"Cargando whisper ({self.model})...")
            self._whisper_model = whisper.load_model(self.model)
            self._model_loaded = True
            logger.info("Modelo cargado (whisper)")
            return True
        except ImportError:
            pass
        
        logger.warning("No hay whisper local disponible")
        return False
    
    def transcribe(self, audio_path: str, language: str = "es") -> Dict:
        """Transcribe un archivo de audio"""
        if not self._model_loaded:
            self.load_model()
        
        if not self._model_loaded:
            return {
                "audio_path": audio_path,
                "language": language,
                "model": self.model,
                "status": "error",
                "error": "Whisper model not available",
                "text": ""
            }
        
        try:
            if hasattr(self._whisper_model, 'transcribe'):
                # faster_whisper
                segments, info = self._whisper_model.transcribe(audio_path, language=language)
                text = " ".join([s.text for s in segments])
            else:
                # openai-whisper
                result = self._whisper_model.transcribe(audio_path, language=language)
                text = result.get("text", "")
            
            return {
                "audio_path": audio_path,
                "language": language,
                "model": self.model,
                "status": "success",
                "text": text.strip()
            }
        except Exception as e:
            logger.error(f"Error transcribiendo audio: {e}")
            return {
                "audio_path": audio_path,
                "language": language,
                "model": self.model,
                "status": "error",
                "error": str(e),
                "text": ""
            }
    
    def transcribe_bytes(self, audio_bytes: bytes, language: str = "es") -> Dict:
        """Transcribe audio desde bytes"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            return self.transcribe(temp_path, language)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    def batch_transcribe(self, folder_path: str) -> List[Dict]:
        """Transcribe múltiples archivos"""
        audio_files = [f for f in os.listdir(folder_path) if f.endswith(('.mp3', '.wav', '.m4a', '.ogg'))]
        results = []
        for f in audio_files:
            path = os.path.join(folder_path, f)
            results.append(self.transcribe(path))
        return results
    
    def get_model_info(self) -> Dict:
        return {
            "current_model": self.model,
            "available_models": self.models,
            "model_loaded": self._model_loaded,
            "for_gem": "music/scholar"
        }


whisper_skill = WhisperSkill()
