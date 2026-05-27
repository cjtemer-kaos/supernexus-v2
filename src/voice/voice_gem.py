#!/usr/bin/env python3
"""
NEXUS IA - Voice Gem Module
Satisfies the dependency for nexus.py and provides basic TTS/STT hooks.
"""

import sys
from pathlib import Path

# Add parent directory to sys.path to allow imports from 01_CORE
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from nexus_tts import speak as tts_speak
except ImportError:
    def tts_speak(text, **kwargs):
        print(f"[TTS FALLBACK] {text}")

class VoiceGem:
    """
    VoiceGem class to handle voice interactions.
    Currently used as a bridge to NexusTTS and AudioController.
    """
    def __init__(self):
        print("[VOICE GEM] Engine initialized.")
        self.active_personality = "sage"

    def speak(self, text: str, personality: str = None):
        """Speaks the given text using the active or provided personality."""
        p = personality or self.active_personality
        print(f"[VOICE GEM] ({p}): {text}")
        tts_speak(text)

    def listen(self, timeout: int = 5):
        """Listens for voice input (placeholder)."""
        print(f"[VOICE GEM] Listening (timeout={timeout}s)...")
        return ""

    def set_personality(self, personality: str):
        """Sets the active speaking personality."""
        self.active_personality = personality
        print(f"[VOICE GEM] Personality set to: {personality}")

if __name__ == "__main__":
    vg = VoiceGem()
    vg.speak("Sistema de voz iniciado correctamente.")
