#!/usr/bin/env python3
"""
NEXUS TTS - Múltiples motores de Text-to-Speech
"""

import asyncio
import edge_tts
import pyttsx3
import tempfile
import os
import threading
from pathlib import Path

VOICES_ES = {
    "es-MX-Dalia": {"name": "Dalia (Mexico)", "gender": "Female", "short": "es-MX-DaliaNeural"},
    "es-MX-Jorge": {"name": "Jorge (Mexico)", "gender": "Male", "short": "es-MX-JorgeNeural"},
    "es-AR-Elena": {"name": "Elena (Argentina)", "gender": "Female", "short": "es-AR-ElenaNeural"},
    "es-AR-Tomas": {"name": "Tomas (Argentina)", "gender": "Male", "short": "es-AR-TomasNeural"},
    "es-CO-Salome": {"name": "Salome (Colombia)", "gender": "Female", "short": "es-CO-SalomeNeural"},
    "es-CO-Gonzalo": {"name": "Gonzalo (Colombia)", "gender": "Male", "short": "es-CO-GonzaloNeural"},
    "es-ES-Ximena": {"name": "Ximena (España)", "gender": "Female", "short": "es-ES-XimenaNeural"},
    "es-CL-Catalina": {"name": "Catalina (Chile)", "gender": "Female", "short": "es-CL-CatalinaNeural"},
    "es-CL-Lorenzo": {"name": "Lorenzo (Chile)", "gender": "Male", "short": "es-CL-LorenzoNeural"},
}


class NexusTTS:
    def __init__(self, motor: str = "pyttsx3", voice: str = None):
        self.motor = motor
        self.voice = voice or "es-MX-Dalia"
        self.rate = 150
        self.volume = 1.0
        
        if motor == "pyttsx3":
            self._init_pyttsx3()
        else:
            self._engine = None
    
    def _init_pyttsx3(self):
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', self.rate)
            self._engine.setProperty('volume', self.volume)
        except:
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
            except:
                pass
    
    def set_rate(self, rate: int):
        self.rate = rate
        if self._engine:
            self._engine.setProperty('rate', rate)
    
    def set_volume(self, volume: float):
        self.volume = volume
        if self._engine:
            self._engine.setProperty('volume', volume)
    
    def speak(self, text: str):
        if self.motor == "edge":
            self._speak_edge(text)
        else:
            self._speak_pyttsx3(text)
    
    def _speak_pyttsx3(self, text: str):
        if self._engine:
            self._engine.say(text)
            self._engine.runAndWait()
    
    def _speak_edge(self, text: str):
        voice_info = VOICES_ES.get(self.voice, VOICES_ES["es-MX-Dalia"])
        
        async def speak():
            communicate = edge_tts.Communicate(text, voice_info["short"])
            
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_file = f.name
            
            await communicate.save(temp_file)
            
            # Reproducir con winsound o similar
            try:
                import winsound
                winsound.PlaySound(temp_file, winsound.SND_FILENAME)
            except:
                pass
            
            try:
                os.unlink(temp_file)
            except:
                pass
        
        asyncio.run(speak())
    
    def get_voices_list(self):
        if self.motor == "edge":
            return VOICES_ES
        else:
            voices = {}
            if self._engine:
                for v in self._engine.getProperty('voices'):
                    voices[v.id] = {"name": v.name, "gender": "Unknown"}
            return voices
    
    def close(self):
        if self._engine:
            self._engine.stop()


tts_engine = NexusTTS(motor="pyttsx3")


def speak(text: str, motor: str = "pyttsx3", voice: str = None):
    engine = NexusTTS(motor=motor, voice=voice)
    engine.speak(text)
    engine.close()