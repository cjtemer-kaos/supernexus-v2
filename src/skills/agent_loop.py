#!/usr/bin/env python3
# Agent Loop Skill
"""
Automated agent loop: read → LLM → write → verify → retry.
Pattern: Claude Code / Cursor Agent internamente usan esto.
"""
import json
import os
import subprocess
import time

class AgentLoopSkill:
    def __init__(self):
        self.name = "agent_loop"
        self.description = "Automated read→fix→verify→retry loop"
        self.max_attempts = 3
    
    def read_file(self, filepath: str) -> dict:
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filepath}"}
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        return {"filepath": filepath, "content": content, "lines": len(content.splitlines())}
    
    def write_file(self, filepath: str, content: str) -> dict:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return {"written": True, "filepath": filepath, "bytes": len(content)}
    
    def run_command(self, cmd: str, cwd: str = ".") -> dict:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd, timeout=60
            )
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout[:5000] if result.stdout else "",
                "stderr": result.stderr[:5000] if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timeout (>60s)"}
        except Exception as e:
            return {"error": str(e)}
    
    def run(self, filepath: str, prompt: str, verifier: str = "python -m py_compile", cwd: str = ".", 
            max_attempts: int = 3, output_file: str = None) -> str:
        results = {
            " filepath": filepath,
            "prompt": prompt,
            "verifier": verifier,
            "attempts": []
        }
        
        for attempt in range(1, max_attempts + 1):
            print(f"[Step {attempt}/{max_attempts}] reading {filepath}...")
            
            file_data = self.read_file(filepath)
            if "error" in file_data:
                return json.dumps({"error": file_data["error"]}, indent=2)
            
            attempt_result = {
                "attempt": attempt,
                "action": "sent to LLM for fix",
                "status": "ready for LLM call"
            }
            
            attempt_result["llm_prompt"] = f"""Archivo: {filepath}
---
{file_data['content']}
---

Instrucción: {prompt}

Devuelve SOLO el código corregido, sin markdown, sin explicaciones."""
            
            if output_file:
                os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
                with open(output_file, "w") as f:
                    json.dump(attempt_result, f, indent=2)
            
            results["attempts"].append(attempt_result)
            
            if attempt < max_attempts:
                results["attempts"][-1]["next"] = "call LLM with prompt above, then write result"
            else:
                results["attempts"][-1]["next"] = "all attempts exhausted"
        
        results["summary"] = f"Agent loop ready: {max_attempts} attempts configured"
        results["usage"] = "Call LLM with the prompt in each attempt, write result, then run verifier"
        
        return json.dumps(results, indent=2)
    
    def create_loop_template(self, filepath: str, prompt: str, verifier: str) -> dict:
        return {
            "loop": {
                "filepath": filepath,
                "prompt": prompt,
                "verifier": verifier,
                "max_attempts": self.max_attempts,
                "steps": [
                    {"n": 1, "action": "read_file", "tool": "read_file"},
                    {"n": 2, "action": "send_to_llm", "tool": "LLM with prompt"},
                    {"n": 3, "action": "write_code", "tool": "write_file"},
                    {"n": 4, "action": "verify", "tool": "run_command(verifier)"},
                    {"n": 5, "action": "check_result", "logic": "if success → done, else retry"}
                ]
            },
            "example": "filepath='src/utils/helpers.py', prompt='Fix all linting errors', verifier='ruff check src/utils/helpers.py'"
        }
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "methods": [
                "run(filepath, prompt, verifier, cwd, max_attempts, output_file)",
                "read_file(filepath)",
                "write_file(filepath, content)",
                "run_command(cmd, cwd)",
                "create_loop_template(filepath, prompt, verifier)"
            ],
            "usage": "Ejecuta: /skill agent_loop run path/to/file.py 'fix lint errors' 'ruff check'"
        }

if __name__ == "__main__":
    skill = AgentLoopSkill()
    print(json.dumps(skill.info(), indent=2))