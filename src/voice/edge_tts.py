import asyncio
import edge_tts
import os

VOICES = {
    "director": "es-ES-ElviraNeural",
    "ejecutivo": "es-ES-AlvaroNeural", 
    "creativo": "es-MX-DaliaNeural",
    "sabio": "es-ES-AlvaroNeural",
    "arquitecto": "es-MX-JorgeNeural",
    "codificador": "es-MX-DaliaNeural"
}

DEFAULT_VOICE = "es-ES-ElviraNeural"

async def speak_async(text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%", pitch: str = "+0Hz", output_file: str = None):
    """Genera audio con edge-tts"""
    if output_file is None:
        output_file = "temp_voice.mp3"
    
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_file)
    return output_file

def speak(text: str, voice: str = DEFAULT_VOICE, rate: str = "+0%", pitch: str = "+0Hz") -> str:
    """Versión síncrona"""
    return asyncio.run(speak_async(text, voice, rate, pitch))

def get_voices():
    return VOICES

def get_all_spanish_voices():
    return [
        ("es-ES-ElviraNeural", "Elvira (España)"),
        ("es-ES-AlvaroNeural", "Álvaro (España)"),
        ("es-MX-DaliaNeural", "Dalia (México)"),
        ("es-MX-JorgeNeural", "Jorge (México)"),
        ("es-AR-ElenaNeural", "Elena (Argentina)"),
        ("es-AR-TomasNeural", "Tomás (Argentina)"),
        ("es-CL-CatalinaNeural", "Catalina (Chile)"),
        ("es-CO-GonzaloNeural", "Gonzalo (Colombia)"),
        ("es-PE-CamilaNeural", "Camila (Perú)"),
        ("es-VE-PaolaNeural", "Paola (Venezuela)"),
    ]

if __name__ == "__main__":
    print("=== Edge-TTS Avatar Voice ===")
    print("Voces por personalidad:")
    for pers, voice in VOICES.items():
        print(f"  {pers}: {voice}")
    
    print("\nPrueba de voz:")
    test = speak("Hola, soy el asistente Nexus IA.", voice="es-ES-ElviraNeural")
    print(f"Generado: {test}")