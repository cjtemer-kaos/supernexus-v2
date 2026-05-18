
import subprocess
import os
import json

class RemotionSkill:
    """
    Skill para automatizar la creación de videos y animaciones usando Remotion.
    Permite renderizar proyectos de React como video MP4.
    """
    def __init__(self):
        self.name = "remotion"
        self.description = "Automatización de video programático con Remotion y React."
        self.cli = "remotion"

    def render(self, project_dir: str, composition_id: str = "Main", out: str = "nexus_render.mp4") -> str:
        """Renderiza una composición de Remotion."""
        if not os.path.exists(project_dir):
            return f"❌ [Remotion] Directorio de proyecto no encontrado: {project_dir}"
        
        cmd = [self.cli, "render", composition_id, out]
        return self._run(cmd, cwd=project_dir)

    def create_project(self, name: str, template: str = "@remotion/template") -> str:
        """Crea un nuevo proyecto de Remotion."""
        cmd = ["npx", "-y", "create-video", name, "--template", template]
        return self._run(cmd)

    def preview(self, project_dir: str) -> str:
        """Inicia el servidor de preview de Remotion."""
        cmd = [self.cli, "preview"]
        # Nota: Esto es un proceso de larga duración
        return self._run(cmd, cwd=project_dir, wait=False)

    def _run(self, cmd: list, cwd: str = None, wait: bool = True) -> str:
        try:
            if not wait:
                subprocess.Popen(cmd, cwd=cwd, shell=True)
                return "[OK] Remotion Preview iniciado en segundo plano."
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, shell=True)
            if result.returncode == 0:
                return f"[OK] {result.stdout}"
            return f"❌ [Remotion Error] {result.stderr or result.stdout}"
        except Exception as e:
            return f"❌ [Remotion Exception] {str(e)}"

if __name__ == "__main__":
    # Test (solo si remotion está instalado)
    rem = RemotionSkill()
    print("Skill Remotion Cargado.")
