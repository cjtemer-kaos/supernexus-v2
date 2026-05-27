"""
Test completo del sistema de avatar animado con personalidad
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.voice.wav2lip_animator import Wav2LipAnimator
from src.voice.nexus_tts import NexusTTS
from src.voice.personality_system import PersonalityManager, InteractionRouter

async def main():
    print("=== Test Avatar Animado con Personalidad ===\n")
    
    # 1. Inicializar sistema de personalidad
    pm = PersonalityManager()
    router = InteractionRouter()
    print(f"[OK] Personalidades disponibles: {pm.list_personalities()}")
    
    # 2. Inicializar TTS
    tts = NexusTTS(motor="edge", voice="es-MX-JorgeNeural")
    print("[OK] TTS inicializado")
    
    # 3. Inicializar Animator
    try:
        animator = Wav2LipAnimator()
        print("[OK] Wav2Lip Animator inicializado")
    except FileNotFoundError as e:
        print(f"[ERROR] {e}")
        return
    
    # 4. Probar detección de personalidad
    test_queries = [
        "Investiga sobre machine learning",
        "Escribe un script en Python",
        "Diseña una interfaz bonita",
        "Analiza estos datos",
        "Revisa la seguridad del sistema",
    ]
    
    print("\n--- Detección de Personalidad ---")
    for query in test_queries:
        result = router.route(query)
        print(f"  '{query}'")
        print(f"    -> Personalidad: {result['personality']} (confianza: {result['confidence']:.2f})")
        print(f"    -> Accion: {result['action']}")
        print()
    
    # 5. Generar video con personalidad
    print("--- Generando Video con Personalidad ---")
    
    # Cambiar a personalidad "sabio"
    pm.set_personality("sabio")
    voice_config = pm.get_voice_config()
    tts.set_voice(voice_config.get("edge_voice", "es-MX-Dalia"))
    
    image_path = r"D:\stream\ninja.jpg"
    text = "Hola, soy Scholar, el sabio de NEXUS. El conocimiento es infinito."
    
    print(f"Personalidad: {pm.current_personality}")
    print(f"Texto: '{text}'")
    print(f"Voz: {voice_config.get('edge_voice')}")
    print(f"Imagen: {image_path}")
    
    try:
        video_path = await animator.generate_from_text(
            image_path=image_path,
            text=text,
            tts_engine=tts,
            output_name="ninja_scholar.mp4"
        )
        print(f"\n[OK] Video generado: {video_path}")
    except Exception as e:
        print(f"\n[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(main())
