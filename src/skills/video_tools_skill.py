#!/usr/bin/env python3
import subprocess
import os
import webbrowser

class VideoToolsSkill:
    def __init__(self):
        self.name = "video_tools"
        self.description = "Gestor de herramientas del ecosistema Nexus basadas en el video de OpenClaw/Claude-Code."
        self.tools = {
            "open-codesign": {
                "name": "Open CoDesign",
                "desc": "Alternativa open-source a Claude Design (Claude Open China).",
                "path": "D:/ias/proyectos/open-codesign",
                "cmd": "pnpm dev"
            },
            "claude-code": {
                "name": "Claude-Code",
                "desc": "CLI oficial de Anthropic para codificación asistida.",
                "cmd": "claude"
            },
            "openclaw": {
                "name": "OpenClaw (Ernie Claw)",
                "desc": "Gateway multi-canal para agentes de IA.",
                "cmd": "openclaw status"
            },
            "opencode": {
                "name": "OpenCode",
                "desc": "Agente de programación open-source (Alternativa a Claude Code).",
                "cmd": "opencode --help"
            },
            "specify": {
                "name": "Specify (Spec-Kit)",
                "desc": "Herramienta de inicialización para Spec-Driven Development (SDD).",
                "cmd": "specify --help"
            },
            "locally-uncensored": {
                "name": "Locally Uncensored (Bolt.diy)",
                "desc": "Interfaz local-first para desarrollo asistido por IA (Optimizado).",
                "path": "D:/ias/proyectos/bolt_diy",
                "cmd": "powershell -ExecutionPolicy Bypass -File start_optimized.ps1"
            },
            "supra-wall": {
                "name": "Supra-Wall",
                "desc": "Capa de seguridad y filtrado para agentes de IA.",
                "url": "https://supra-wall.com"
            }
        }
        self.links = {
            "kimi": "https://kimi.moonshot.cn/",
            "glm": "https://chatglm.cn/",
            "deepseek": "https://chat.deepseek.com/",
            "qwen": "https://tongyi.aliyun.com/",
            "sonauto": "https://sonauto.ai/",
            "mureka": "https://mureka.ai/",
            "lovable": "https://lovable.dev/",
            "ga4_copilot": "https://ga4copilot.com/",
            "notion_portals": "https://notionportals.com/",
            "openspec": "https://openspec.org/"
        }

    def list_tools(self):
        """Lista las herramientas instaladas y disponibles."""
        return {
            "installed_tools": self.tools,
            "web_links": self.links
        }

    def launch(self, tool_id: str):
        """Lanza una herramienta o abre su link."""
        if tool_id in self.tools:
            tool = self.tools[tool_id]
            cmd = tool.get("cmd")
            cwd = tool.get("path", os.getcwd())
            try:
                # Se lanza en una nueva terminal de Windows
                subprocess.Popen(f'start cmd /k "{cmd}"', shell=True, cwd=cwd)
                return f"[Success] Lanzando {tool['name']} en una nueva terminal."
            except Exception as e:
                return f"[Error] No se pudo lanzar {tool_id}: {str(e)}"
        
        if tool_id in self.links:
            url = self.links[tool_id]
            webbrowser.open(url)
            return f"[Success] Abriendo {tool_id} en el navegador: {url}"

        return f"[Error] Herramienta '{tool_id}' no encontrada."

    def launch_dual_terminal(self):
        """Lanza el sistema de doble terminal: Claude Oficial + Open CoDesign."""
        try:
            # Terminal 1: Claude Oficial
            subprocess.Popen('start cmd /k "claude"', shell=True)
            # Terminal 2: Open CoDesign
            cwd = "D:/ias/proyectos/open-codesign"
            subprocess.Popen('start cmd /k "pnpm dev"', shell=True, cwd=cwd)
            return "[Success] Sistema de Doble Terminal iniciado."
        except Exception as e:
            return f"[Error] No se pudo iniciar la doble terminal: {str(e)}"

    def info(self):
        return {
            "name": self.name,
            "description": self.description,
            "tools_count": len(self.tools),
            "links_count": len(self.links)
        }
