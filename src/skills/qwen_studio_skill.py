# Qwen Studio Integration - NEXUS IA
# Alternativa gratuita a ChatGPT/Gemini

class QwenStudioSkill:
    def __init__(self):
        self.name = 'qwen'
        self.executable = r'C:\Program Files\Qwen\Qwen.exe'
        self.port = 11180
        
    def is_running(self):
        import subprocess
        try:
            result = subprocess.run(['tasklist'], capture_output=True, text=True)
            return 'Qwen.exe' in result.stdout
        except:
            return False
        
    def launch(self):
        import subprocess
        subprocess.Popen(self.executable)
        return 'Qwen Studio iniciada'
        
    def info(self):
        return {
            'skill': self.name,
            'executable': self.executable,
            'local_api': f'http://localhost:{self.port}',
            'methods': ['is_running()', 'launch()']
        }
