# SSH Management Skill - NEXUS IA
# Gestiona SSH bidirectional ${USERNAME} ↔ Remote Node

import subprocess
import os

class SSHSkill:
    def __init__(self):
        self.name = "ssh"
        self.description = "Gestiona SSH bidirectional"
        
    def is_sshd_running(self):
        try:
            result = subprocess.run(['sc', 'query', 'sshd'], capture_output=True, text=True)
            return 'RUNNING' in result.stdout
        except:
            return False
    
    def start_sshd(self):
        try:
            subprocess.run(['net', 'start', 'sshd'], capture_output=True)
            return "SSH daemon started"
        except Exception as e:
            return f"Error: {e}"
    
    def stop_sshd(self):
        try:
            subprocess.run(['net', 'stop', 'sshd'], capture_output=True)
            return "SSH daemon stopped"
        except Exception as e:
            return f"Error: {e}"
    
    def get_sshd_status(self):
        running = self.is_sshd_running()
        return {
            "sshd": "running" if running else "stopped",
            "port": 22
        }
    
    def check_tailscale(self):
        try:
            result = subprocess.run(['tailscale', 'status'], capture_output=True, text=True)
            return "Tailscale running"
        except:
            return "Tailscale not installed"
    
    def start_tailscale(self):
        try:
            subprocess.run(['start', 'tailscale'], capture_output=True)
            return "Tailscale starting"
        except:
            return "Install Tailscale from tailscale.com"
    
    def enable_firewall_ssh(self):
        try:
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', 'name=SSH', 'dir=in', 'action=allow', 'protocol=TCP', 'localport=22'], capture_output=True)
            return "Firewall rule added"
        except:
            return "Firewall rule exists"
    
    def info(self):
        return {
            "skill": self.name,
            "description": self.description,
            "port": 22,
            "methods": ["get_sshd_status()", "start_sshd()", "stop_sshd()", "check_tailscale()", "start_tailscale()"]
        }