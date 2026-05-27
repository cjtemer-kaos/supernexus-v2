#!/usr/bin/env python3
"""
Audio Controller - Control de micrófono y reconocimiento de voz para Nexus
Autor: Nexus IA
Usado por: mic_control.py
"""

import os
import sys
import io
import tempfile
import threading
import numpy as np
from pathlib import Path

OLLAMA_SERVER = "http://localhost:11434"
WHISPER_MODEL = "base"

class AudioController:
    def __init__(self, model: str = "base"):
        self.model = model
        self.audio = None
        self.model_loaded = False
        self.whisper_model = None
        self._init_audio()
    
    def _init_audio(self):
        """Inicializa captura de audio"""
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            
            # Usar el dispositivo predeterminado de Windows
            default_input = p.get_default_input_device_info()
            self.input_device = default_input['index']
            print(f"[AUDIO] Mic predeterminado: {self.input_device} - {default_input['name']}")
            
            self.audio = p
            self.CHUNK = 1024
            self.FORMAT = pyaudio.paInt16
            self.CHANNELS = 1
            self.RATE = 16000
            self._audio_ready = True
            print(f"[AUDIO] Micrófono listo")
            
            # Cargar modelo de reconocimiento de voz
            self.load_model()
            
        except ImportError:
            self._audio_ready = False
            print("[AUDIO] PyAudio no instalado")
        except Exception as e:
            self._audio_ready = False
            print(f"[AUDIO] Error: {e}")
    
    def load_model(self):
        """Carga modelo de reconocimiento de voz"""
        try:
            from faster_whisper import WhisperModel
            print(f"[AUDIO] Cargando faster-whisper ({self.model})...")
            self.whisper_model = WhisperModel(self.model, device="cpu", compute_type="int8")
            self.model_loaded = True
            print("[AUDIO] Modelo cargado (faster-whisper)")
            return True
        except ImportError:
            pass
        
        try:
            import whisper
            print(f"[AUDIO] Cargando whisper ({self.model})...")
            self.whisper_model = whisper.load_model(self.model)
            self.model_loaded = True
            print("[AUDIO] Modelo cargado (whisper)")
            return True
        except ImportError:
            pass
        
        print("[AUDIO] No hay whisper local. Usando Ollama como fallback.")
        self.model_loaded = False
        return False
    
    def _capture_audio(self, duration: float = 3.0) -> bytes:
        """Captura audio del micrófono"""
        if not self._audio_ready:
            return b""
        
        frames = []
        chunks = int(self.RATE / self.CHUNK * duration)
        
        try:
            device_index = getattr(self, 'input_device', 0)
            stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.CHUNK
            )
            
            for _ in range(chunks):
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            return b''.join(frames)
        except Exception as e:
            print(f"[AUDIO] Error capturando: {e}")
            return b""
    
    def _recognize_faster_whisper(self, audio_bytes: bytes) -> tuple:
        """Reconocimiento con faster-whisper"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            segments, info = self.whisper_model.transcribe(temp_path, language="es")
            text = " ".join([s.text for s in segments])
            lang = info.language or "es"
            return text, lang
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _recognize_whisper(self, audio_bytes: bytes) -> tuple:
        """Reconocimiento con whisper original"""
        import whisper
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            result = self.whisper_model.transcribe(temp_path, language="es")
            return result["text"], "es"
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def _recognize_ollama(self, audio_bytes: bytes) -> tuple:
        """Fallback: usar Ollama para transcripción simulada"""
        try:
            import requests
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            
            try:
                with open(temp_path, "rb") as audio_file:
                    import base64
                    audio_b64 = base64.b64encode(audio_file.read()).decode()
                
                prompt = """Analiza este audio y extrae el texto spoken. 
Responde SOLO con el texto detectado en español, o "sin audio" si no hay voz clara."""
                
                response = requests.post(
                    f"{OLLAMA_SERVER}/api/generate",
                    json={
                        "model": "whisper",
                        "prompt": prompt,
                        "images": [audio_b64] if audio_b64 else [],
                        "stream": False
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json().get("response", "sin audio"), "es"
            finally:
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except Exception as e:
            print(f"[AUDIO] Ollama fallback error: {e}")
        
        return "sin audio", "es"
    
    def recognize(self, audio_bytes: bytes) -> tuple:
        """Reconoce texto del audio"""
        if not audio_bytes:
            return "sin audio", "es"
        
        if self.model_loaded and self.whisper_model:
            try:
                return self._recognize_faster_whisper(audio_bytes)
            except Exception as e:
                print(f"[AUDIO] faster-whisper error: {e}")
                try:
                    return self._recognize_whisper(audio_bytes)
                except:
                    pass
        
        return self._recognize_ollama(audio_bytes)
    
    def listen_for_command(self, timeout: float = 3.0) -> tuple:
        """Escucha comando de voz (para mic_control.py)
        Retorna: (texto, idioma)
        """
        print(f"[AUDIO] Escuchando... ({timeout}s)")
        
        audio_bytes = self._capture_audio(duration=timeout)
        
        if not audio_bytes:
            return "", "es"
        
        text, lang = self.recognize(audio_bytes)
        
        return text.strip(), lang
    
    def listen_continuous(self, callback, stop_event: threading.Event):
        """Escucha continua con callback"""
        print("[AUDIO] Modo continuo iniciado")
        
        while not stop_event.is_set():
            audio_bytes = self._capture_audio(duration=2.0)
            if audio_bytes:
                text, lang = self.recognize(audio_bytes)
                if text and text != "sin audio":
                    callback(text, lang)
    
    def transcribe_file(self, file_path: str) -> dict:
        """Transcribe archivo de audio"""
        if not os.path.exists(file_path):
            return {"error": "Archivo no encontrado"}
        
        try:
            import requests
            
            with open(file_path, "rb") as f:
                audio_data = f.read()
            
            audio_b64 = base64.b64encode(audio_data).decode()
            
            response = requests.post(
                f"{OLLAMA_SERVER}/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": "Extrae el texto hablado de este audio. Si no hay voz, responde 'sin audio'.",
                    "images": [audio_b64],
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return {"text": response.json().get("response", ""), "language": "es"}
        except Exception as e:
            return {"error": str(e)}
        
        return {"error": "Transcripción fallida"}
    
    def close(self):
        """Cierra recursos"""
        if self.audio:
            self.audio.terminate()
            self.audio = None
        print("[AUDIO] Cerrado")


def main():
    """Test del audio controller"""
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    controller = AudioController("base")
    
    print("=" * 40)
    print("Audio Controller - Test")
    print("=" * 40)
    print("Cargando modelo...")
    
    controller.load_model()
    
    print("\nPresiona ENTER para escuchar (Ctrl+C para salir)")
    
    while True:
        try:
            input()
            text, lang = controller.listen_for_command(timeout=3)
            print(f">>> '{text}' ({lang})")
        except KeyboardInterrupt:
            break
    
    controller.close()
    print("Chao!")


if __name__ == "__main__":
    main()