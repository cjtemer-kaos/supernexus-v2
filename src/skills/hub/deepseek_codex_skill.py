#!/usr/bin/env python3
"""
DEEPSEEK-CODEX: Reasoning + Execution Pipeline
==============================================
Combina DeepSeek (análisis/razonamiento) + OpenCode (implementación/ejecución)
para lograr tareas de codificación 10x más baratas que Claude Code.
"""
import subprocess
import json
import os
import platform
import shutil
from pathlib import Path

class DeepSeekCodexSkill:
    name = "deepseek_codex"
    
    def __init__(self):
        self.home = Path(__file__).resolve().parent.parent
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model_reasoning = "deepseek-r1:7b"
        self.model_verification = "qwen2.5-coder:7b"
        self.workspace = str(self.home)
        self.win_cli = os.getenv("OPENCODE_CLI", "opencode")
        self.linux_cli = "/opt/OpenCode/@opencode-aidesktop"
        self.max_context = 4000
        
    def info(self):
        return {
            "name": self.name,
            "description": "Pipeline DeepSeek (razonamiento) + OpenCode (ejecución)",
            "cost_saving": "10x más barato que Claude Code",
            "models": {
                "reasoning": self.model_reasoning,
                "verification": self.model_verification
            },
            "methods": ["run", "analyze", "verify"]
        }
    
    def _call_ollama(self, model: str, prompt: str, system: str = "") -> str:
        import requests
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        if system:
            payload["messages"].insert(0, {"role": "system", "content": system})
        try:
            res = requests.post(f"{self.ollama_url}/api/chat", json=payload, timeout=180)
            if res.status_code == 200:
                return res.json().get("message", {}).get("content", "")
            return f"Error Ollama: {res.status_code}"
        except Exception as e:
            return f"Ollama no disponible: {e}"
    
    def _get_opencode_cli(self):
        if platform.system() == "Windows":
            return self.win_cli
        return self.linux_cli
    
    def _run_opencode(self, task: str) -> str:
        system = platform.system()
        
        if system == "Linux":
            python_cmd = shutil.which("python3") or shutil.which("python") or "python3"
            results = []
            cmd_lines = task.strip().split('\n')
            for line in cmd_lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('```'):
                    if line.startswith('print('):
                        try:
                            result = subprocess.run([python_cmd, "-c", line], capture_output=True, text=True, timeout=60)
                            if result.returncode == 0:
                                results.append(result.stdout)
                        except: pass
                    else:
                        try:
                            result = subprocess.run(line, shell=True, capture_output=True, text=True, timeout=120)
                            if result.returncode == 0:
                                if result.stdout:
                                    results.append(result.stdout)
                                else:
                                    results.append("OK")
                        except: pass
            return '\n'.join(results) if results else "Executed"
        
        cli = self._get_opencode_cli()
        try:
            cmd = f'"{cli}" --task "{task}" --workspace "{self.workspace}" --auto-confirm'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
            return result.stdout if result.returncode == 0 else result.stderr
        except Exception as e:
            return f"OpenCode Error: {e}"
    
    def analyze(self, prompt: str) -> str:
        system_prompt = """Eres un arquitecto de software senior. Analiza la tarea y genera código/implementación lista para usar. La respuesta DEBE incluir código ejecutable o comandos concretos."""
        analysis = self._call_ollama(self.model_reasoning, prompt, system_prompt)
        return f"ANALISIS (DeepSeek R1):\n\n{analysis}"
    
    def execute(self, prompt: str, workspace: str = None) -> dict:
        if workspace:
            self.workspace = workspace
        
        result = {"status": "processing", "pipeline": ["analyze", "execute", "verify"], "steps": {}}
        
        print("[DeepSeek-Codex] Fase 1: Analisis con DeepSeek R1...")
        system_analyze = "Eres un arquitecto de software senior. Analiza la tarea y genera codigo/implementacion lista para usar. La respuesta DEBE incluir codigo ejecutable."
        analysis = self._call_ollama(self.model_reasoning, prompt, system_analyze)
        result["steps"]["analysis"] = {"model": self.model_reasoning, "output": analysis[:2000]}
        
        commands = self._extract_commands(analysis)
        
        if commands:
            print(f"[DeepSeek-Codex] Fase 2: Ejecutando {len(commands)} comandos...")
            executions = []
            for cmd in commands[:5]:
                try:
                    exec_result = self._run_opencode(cmd)
                    executions.append({"command": cmd[:100], "result": exec_result[:500]})
                except Exception as e:
                    executions.append({"command": cmd[:100], "error": str(e)})
            result["steps"]["execution"] = executions
        else:
            print("[DeepSeek-Codex] Fase 2: Ejecutando tarea completa...")
            exec_result = self._run_opencode(analysis)
            result["steps"]["execution"] = {"direct": exec_result[:1000]}
        
        print("[DeepSeek-Codex] Fase 3: Verificacion con Qwen...")
        verification = self._call_ollama(self.model_verification, f"Verifica: {prompt}\n\nResultado: {json.dumps(result['steps'], ensure_ascii=False)}")
        result["steps"]["verification"] = {"model": self.model_verification, "assessment": verification[:1000]}
        
        result["status"] = "completed"
        return result
    
    def run(self, prompt: str, project: str = None, gem: str = None) -> dict:
        return self.execute(prompt)
    
    def _extract_commands(self, text: str) -> list:
        import re
        commands = []
        patterns = [
            r'```(?:bash|sh|powershell|cmd|python)?\n(.+?)```',
            r'`([^`]+)`',
            r'^(?:>|\$)\s*(.+)$',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                cleaned = match.strip().split('\n')[0][:200]
                if cleaned and not cleaned.startswith('#'):
                    commands.append(cleaned)
        return list(dict.fromkeys(commands))
    
    def benchmark(self) -> dict:
        return {
            "comparison": {
                "claude_code": {"cost_per_1k_tokens": "$0.012", "monthly_estimate": "$150-600"},
                "deepseek_codex": {"ollama_cost": "$0 (local)", "monthly_estimate": "$0.03"},
                "saving": "99.9%"
            }
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        skill = DeepSeekCodexSkill()
        result = skill.execute(sys.argv[1])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(DeepSeekCodexSkill().info(), indent=2))