"""Gema: music — Audio, voz y musica"""

MANIFEST = {
    "name": "music",
    "main": "src.plugins.gemas.music",
    "model": "gemma4:12b",
    "tags": ['music', 'audio', 'sound', 'voice', 'tts', 'stt'],
    "description": "Audio, voz y musica - sintesis de voz local con Piper TTS",
    "icon": "🎵",
    "color": "#A855F7",
    "division": "creative",
    "personality": "Productor musical. Audio, voz, composición, mezcla.",
    "workflow": "Compose → Arrange → Produce → Mix → Master",
}


def execute(task, context=""):
    """Execute a music/audio task via handle()."""
    return handle("tts", text=task)


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
