
#!/usr/bin/env python3
import subprocess
import os
import platform

class OpenCodeSkill:
    def __init__(self):
        self.name = "opencode"
        self.description = "Ejecuta tareas autónomas usando el motor OpenCode (Back-end)."
        # En la distro usamos la ruta estándar por defecto
        self.win_cli = os.getenv("OPENCODE_PATH", r"C:\Program Files\OpenCode\OpenCode.exe")
        self.linux_cli = "opencode" 
        
    def execute(self, task: str, workspace: str = None, model: str = "ollama-cloud/minimax-m2.5") -> str:
        """Ejecuta una tarea delegándola al motor OpenCode en segundo plano."""
        is_win = platform.system() == "Windows"
        cli = self.win_cli if is_win else self.linux_cli
        
        if not workspace:
            workspace = os.getcwd()
            
        try:
            # Sintaxis moderna: opencode run [message] --model [model] --dir [dir]
            cmd = [cli, "run", task, "--model", model, "--dir", workspace, "--dangerously-skip-permissions"]
            
            kwargs = {'capture_output': True, 'text': True, 'cwd': workspace}
            if is_win:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                kwargs['startupinfo'] = startupinfo
                kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                
            # Limpiamos el entorno de llaves que puedan causar conflictos
            env = os.environ.copy()
            env.pop("OPENROUTER_API_KEY", None)
            env.pop("302AI_API_KEY", None)
            kwargs['env'] = env
                
            result = subprocess.run(cmd, **kwargs)
            if result.returncode == 0:
                return {"response": result.stdout or "Tarea completada por OpenCode (sin salida)."}
            else:
                err_msg = result.stderr or result.stdout or "Error desconocido (proceso sin salida)"
                return {"response": f"Error de OpenCode: {err_msg}"}
        except Exception as e:
            return {"response": f"Fallo Crítico: {str(e)}"}
