"""Gema: music — Audio, voz y musica"""

MANIFEST = {
    "name": "music",
    "tags": ['music', 'audio', 'sound', 'voice', 'tts', 'stt'],
    "description": "Audio, voz y musica - sintesis de voz local con Piper TTS",
    "model": "carstenuhlig/omnicoder-2-9b:q4_k_m",
}


def handle(action, text=None, voice=None):
    """Handle TTS/audio actions via Piper TTS."""
    if action == "tts" and text:
        from src.core.voice_engine import get_engine
        engine = get_engine()
        if not engine.available:
            return {"error": "Voice engine not available"}
        if voice:
            engine.set_voice(voice)
        out_path = engine.speak(text)
        return {"success": True, "path": out_path, "voice": engine.voice_name}
    return {"error": f"Unknown action: {action}"}
