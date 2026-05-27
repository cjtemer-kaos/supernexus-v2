"""
Genera videos de prueba con todas las personalidades
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.voice.wav2lip_animator import Wav2LipAnimator
from src.voice.nexus_tts import NexusTTS
from src.voice.personality_system import PersonalityManager

async def main():
    print("=== Generando Videos de Prueba por Personalidad ===\n")
    
    pm = PersonalityManager()
    tts = NexusTTS(motor="edge")
    animator = Wav2LipAnimator()
    
    image_path = os.getenv("NEXUS_TEST_IMAGE", str(Path(__file__).parent / "assets" / "ninja.jpg"))
    output_dir = Path(os.getenv("NEXUS_VOICE_OUTPUT", str(Path(__file__).parent / "assets")))
    animator.output_dir = output_dir
    
    # Textos por personalidad
    texts = {
        "director": "Sistema en linea. Soy el Director de NEXUS. ¿Que necesitas, jefe?",
        "ejecutivo": "Listo para la accion. Soy el Ejecutivo. ¿Que construimos hoy?",
        "creativo": "La inspiracion fluye. Soy Muse. ¿Que creamos juntos?",
        "sabio": "El conocimiento es infinito. Soy Scholar. ¿Que quieres aprender?",
        "codificador": "Terminal lista. Soy Codex. ¿Que programamos?",
        "analista": "Los datos no mienten. Soy Analyst. ¿Que analizamos?",
        "seguridad": "Sistemas protegidos. Soy Guardian. ¿Que auditamos?",
    }
    
    for personality, text in texts.items():
        pm.set_personality(personality)
        voice_config = pm.get_voice_config()
        tts.set_voice(voice_config.get("edge_voice", "es-MX-Dalia"))
        
        print(f"Generando: {personality} ({voice_config.get('edge_voice')})")
        
        try:
            video_path = await animator.generate_from_text(
                image_path=image_path,
                text=text,
                tts_engine=tts,
                output_name=f"ninja_{personality}.mp4"
            )
            print(f"  OK: {video_path}")
        except Exception as e:
            print(f"  ERROR: {e}")
        
        print()
    
    print("=== Videos Generados ===")
    for f in output_dir.glob("ninja_*.mp4"):
        print(f"  {f.name}")

if __name__ == "__main__":
    asyncio.run(main())
