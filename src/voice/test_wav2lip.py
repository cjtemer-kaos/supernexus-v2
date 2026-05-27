"""
Test de Wav2Lip Animator para SuperNEXUS v2
"""

import asyncio
import sys
from pathlib import Path

# Agregar project root al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.voice.wav2lip_animator import Wav2LipAnimator
from src.voice.nexus_tts import NexusTTS

async def main():
    print("=== Test Wav2Lip Animator ===")
    
    # 1. Inicializar TTS
    tts = NexusTTS(motor="edge", voice="es-MX-Dalia")
    print("[OK] TTS inicializado")
    
    # 2. Inicializar Animator
    try:
        animator = Wav2LipAnimator()
        print("[OK] Wav2Lip Animator inicializado")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return
    
    # 3. Generar video
    image_path = os.getenv("NEXUS_TEST_IMAGE", str(Path(__file__).parent / "assets" / "ninja.jpg"))
    text = "Hola, soy NEXUS. Tu asistente de inteligencia artificial."
    
    print(f"\nGenerando video para: '{text}'")
    print(f"Imagen: {image_path}")
    
    try:
        video_path = await animator.generate_from_text(
            image_path=image_path,
            text=text,
            tts_engine=tts,
            output_name="test_ninja.mp4"
        )
        print(f"\n[OK] Video generado: {video_path}")
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(main())
