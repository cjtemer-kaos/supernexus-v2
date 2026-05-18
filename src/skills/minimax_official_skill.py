
import subprocess
import os
import json

class MinimaxOfficialSkill:
    """
    Skill oficial de MiniMax utilizando mmx-cli para capacidades multimodales.
    Permite generar texto, imágenes, video, audio y música.
    """
    def __init__(self):
        self.name = "minimax_official"
        self.description = "Capacidades multimodales oficiales de MiniMax (Texto, Imagen, Video, Audio, Música, Búsqueda)."
        self.cli = "mmx"

    def chat(self, message: str, model: str = "MiniMax-M2.7-highspeed", system: str = None) -> str:
        cmd = [self.cli, "text", "chat", "--message", message, "--model", model]
        if system:
            cmd.extend(["--system", system])
        return self._run(cmd)

    def generate_image(self, prompt: str, aspect_ratio: str = "16:9", n: int = 1) -> str:
        cmd = [self.cli, "image", "generate", "--prompt", prompt, "--aspect-ratio", aspect_ratio, "--n", str(n)]
        return self._run(cmd)

    def generate_video(self, prompt: str, out: str = "nexus_video.mp4") -> str:
        # Nota: La generación de video es asíncrona por defecto en mmx-cli si se usa --download
        cmd = [self.cli, "video", "generate", "--prompt", prompt, "--download", out]
        return self._run(cmd)

    def tts(self, text: str, out: str = "nexus_audio.mp3", voice: str = "English_magnetic_voiced_man") -> str:
        cmd = [self.cli, "speech", "synthesize", "--text", text, "--out", out, "--voice", voice]
        return self._run(cmd)

    def generate_music(self, prompt: str, lyrics: str = None, instrumental: bool = False, out: str = "nexus_song.mp3") -> str:
        cmd = [self.cli, "music", "generate", "--prompt", prompt, "--out", out]
        if lyrics:
            cmd.extend(["--lyrics", lyrics])
        if instrumental:
            cmd.append("--instrumental")
        return self._run(cmd)

    def search(self, query: str) -> str:
        cmd = [self.cli, "search", "query", "--q", query]
        return self._run(cmd)

    def _run(self, cmd: list) -> str:
        try:
            # mmx-cli usa el API Key de ~/.mmx/config.json o la variable de entorno
            env = os.environ.copy()
            # Aseguramos que use la llave de 302ai si es compatible o la nativa de Minimax
            api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("302AI_API_KEY")
            if api_key:
                env["MINIMAX_API_KEY"] = api_key
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if result.returncode == 0:
                return result.stdout
            return f"❌ [MMX-CLI Error] {result.stderr or result.stdout}"
        except Exception as e:
            return f"❌ [MMX-CLI Exception] {str(e)}"

if __name__ == "__main__":
    mmx = MinimaxOfficialSkill()
    # Test simple
    print(mmx.chat("Hola, ¿quién eres?"))
