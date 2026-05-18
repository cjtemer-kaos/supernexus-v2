"""Voz y audio - Captura de microfono, STT con Whisper, TTS multi-motor"""
from src.voice.audio_controller import AudioController
from src.voice.nexus_tts import NexusTTS
from src.voice.voice_gem import VoiceGem
from src.voice.edge_tts import speak as edge_tts_speak, speak_async as edge_tts_speak_async, get_voices as get_edge_voices
from src.voice.whisper_skill import WhisperSkill, whisper_skill
from src.voice.voice_cloning import VoiceCloningSkill

__all__ = [
    "AudioController",
    "NexusTTS",
    "VoiceGem",
    "edge_tts_speak",
    "edge_tts_speak_async",
    "get_edge_voices",
    "WhisperSkill",
    "whisper_skill",
    "VoiceCloningSkill",
]
