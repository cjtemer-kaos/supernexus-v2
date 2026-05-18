"""
Wav2Lip Animator para SuperNEXUS v2
Integra TTS con Wav2Lip para generar video lip-sync desde una imagen estatica
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

WAV2LIP_PATH = Path(os.getenv("NEXUS_WAV2LIP_PATH", str(Path.home() / "Wav2Lip")))
CHECKPOINT_PATH = WAV2LIP_PATH / "checkpoints" / "wav2lip_gan.pth"
FACE_DETECTOR_PATH = WAV2LIP_PATH / "face_detection" / "detection" / "sfd" / "s3fd.pth"

class Wav2LipAnimator:
    """Genera video lip-sync usando Wav2Lip"""

    def __init__(self, 
                 checkpoint: Optional[str] = None,
                 face_detector: Optional[str] = None,
                 output_dir: Optional[str] = None):
        self.checkpoint = checkpoint or str(CHECKPOINT_PATH)
        self.face_detector = face_detector or str(FACE_DETECTOR_PATH)
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir()) / "nexus_avatar"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._verify_models()

    def _verify_models(self):
        """Verifica que los modelos existen"""
        if not Path(self.checkpoint).exists():
            raise FileNotFoundError(
                f"Checkpoint Wav2Lip no encontrado: {self.checkpoint}\n"
                "Descargalo en: https://iiitaphyd-my.sharepoint.com/:u:/g/personal/radrabha_m_research_iiit_ac_in/Eb3LEzbfuKlJiR600lQWRxgBIY27JZg80f7V9jtMfbNDaQ"
            )
        if not Path(self.face_detector).exists():
            raise FileNotFoundError(
                f"Face detector no encontrado: {self.face_detector}\n"
                "Descargalo en: https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth"
            )
        logger.info("Wav2Lip modelos verificados")

    async def generate(self, 
                      image_path: str, 
                      audio_path: str, 
                      output_name: str = "output.mp4",
                      fps: int = 25,
                      resize_factor: int = 1,
                      pads: list = [0, 10, 0, 0]) -> str:
        """
        Genera video lip-sync
        
        Args:
            image_path: Ruta a imagen de referencia (JPG/PNG)
            audio_path: Ruta a archivo de audio (WAV/MP3)
            output_name: Nombre del archivo de salida
            fps: Frames por segundo
            resize_factor: Factor de redimension (1=original, 2=mitad)
            pads: Padding [top, bottom, left, right] para ajustar cara
            
        Returns:
            Ruta al video generado
        """
        output_path = self.output_dir / output_name
        
        cmd = [
            "python", str(WAV2LIP_PATH / "inference.py"),
            "--checkpoint_path", self.checkpoint,
            "--face", image_path,
            "--audio", audio_path,
            "--outfile", str(output_path),
            "--fps", str(fps),
            "--resize_factor", str(resize_factor),
            "--pads", str(pads[0]), str(pads[1]), str(pads[2]), str(pads[3]),
            "--face_det_batch_size", "16",
            "--static", "True"
        ]

        logger.info(f"Ejecutando Wav2Lip: {' '.join(cmd)}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._run_command, cmd)
        
        if output_path.exists():
            logger.info(f"Video generado: {output_path}")
            return str(output_path)
        else:
            raise RuntimeError("Wav2Lip fallo al generar el video")

    def _run_command(self, cmd):
        """Ejecuta comando de forma sincrona"""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(WAV2LIP_PATH)
        )
        if result.returncode != 0:
            logger.error(f"Wav2Lip error: {result.stderr}")
            raise RuntimeError(f"Wav2Lip fallo: {result.stderr}")
        logger.info(f"Wav2Lip output: {result.stdout}")

    async def generate_from_text(self, 
                                image_path: str, 
                                text: str, 
                                tts_engine,
                                output_name: str = "output.mp4") -> str:
        """
        Genera video desde texto (TTS + Wav2Lip)
        
        Args:
            image_path: Imagen de referencia
            text: Texto a hablar
            tts_engine: Instancia de NexusTTS
            output_name: Nombre de salida
            
        Returns:
            Ruta al video
        """
        # 1. Generar audio con TTS
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            audio_path = f.name
        
        try:
            await tts_engine.speak_to_file(text, audio_path)
            
            # 2. Generar video con Wav2Lip
            video_path = await self.generate(
                image_path=image_path,
                audio_path=audio_path,
                output_name=output_name
            )
            return video_path
        finally:
            # Limpiar audio temporal
            if os.path.exists(audio_path):
                os.unlink(audio_path)
