#!/usr/bin/env python3
"""Samba Skill - Compartir carpetas en red Windows/Linux"""
import subprocess

class SambaSkill:
    def __init__(self):
        self.name = "samba"
        self.description = "Compartir carpetas via Samba en red local"
        self.smb_conf = "/etc/samba/smb.conf"
    
    def info(self):
        return {"skill": self.name, "description": self.description}
    
    def status(self):
        """Estado de Samba"""
        result = subprocess.run(["systemctl", "status", "smbd"], capture_output=True, text=True)
        return {"smbd": result.stdout[:500]}
    
    def shares(self):
        """Ver recursos compartidos"""
        result = subprocess.run(["smbclient", "-L", "localhost", "-U", "guest"], capture_output=True, text=True)
        return {"shares": result.stdout}
    
    def list_shares(self):
        """Listar shares activos"""
        result = subprocess.run(["net", "share"], capture_output=True, text=True)
        return {"shares": result.stdout}
    
    def add_share(self, name, path, comment=""):
        """Agregar share"""
        config = f"""
[{name}]
path = {path}
browseable = yes
writeable = yes
guest ok = yes
comment = {comment}
"""
        with open("/tmp/smb_temp.conf", "w") as f:
            f.write(config)
        result = subprocess.run(["sudo", "sh", "-c", f"cat /tmp/smb_temp.conf >> {self.smb_conf}"], capture_output=True, text=True)
        subprocess.run(["sudo", "systemctl", "restart", "smbd"])
        return {"share": name, "path": path, "result": "added"}
    
    def restart(self):
        """Reiniciar Samba"""
        result = subprocess.run(["sudo", "systemctl", "restart", "smbd"], capture_output=True, text=True)
        return {"result": result.returncode == 0}

if __name__ == "__main__":
    skill = SambaSkill()
    print(skill.info())