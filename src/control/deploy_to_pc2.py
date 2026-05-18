import paramiko
import os

def deploy():
    host = os.getenv("SUPER_NEXUS_Remote Node_IP", "")
    user = os.getenv("SUPER_NEXUS_Remote Node_USER", "")
    pw = os.getenv("SUPER_NEXUS_Remote Node_PASSWORD", "")

    if not host or not user:
        print("[!] Remote node not configured. Set SUPER_NEXUS_Remote Node_IP and SUPER_NEXUS_Remote Node_USER in .env")
        return

    print(f"[*] Conectando a nodo remoto ({host})...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw, timeout=10)

    sftp = ssh.open_sftp()

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    remote_base = f"/home/{user}/Escritorio/NEXUS/nexus-ia"

    files_to_transfer = {
        os.path.join(project_root, "src", "agents", "nexus_autonomous_loop.py"): f"{remote_base}/nexus_autonomous_loop.py",
        os.path.join(project_root, "src", "security", "nexus_suprawall.py"): f"{remote_base}/nexus_suprawall.py"
    }

    for local, remote in files_to_transfer.items():
        if os.path.exists(local):
            print(f"[*] Subiendo {os.path.basename(local)} -> {remote}...")
            sftp.put(local, remote)
        else:
            print(f"[!] File not found: {local}")

    print(f"[*] Asegurando existencia de /home/{user}/.nexus/brain...")
    ssh.exec_command(f"mkdir -p /home/{user}/.nexus/brain")

    nexus_brain = os.path.expanduser("~/.nexus/brain")
    mem_files = {
        os.path.join(nexus_brain, "findings.md"): f"/home/{user}/.nexus/brain/findings.md",
        os.path.join(nexus_brain, "decisions.md"): f"/home/{user}/.nexus/brain/decisions.md",
        os.path.join(nexus_brain, "cloud.md"): f"/home/{user}/.nexus/brain/cloud.md"
    }

    for local, remote in mem_files.items():
        if os.path.exists(local):
            print(f"[*] Subiendo {os.path.basename(local)} -> {remote}...")
            sftp.put(local, remote)
        else:
            print(f"[!] File not found: {local}")

    sftp.close()

    print("[*] Ajustando permisos en nodo remoto...")
    ssh.exec_command(f"chmod +x {remote_base}/nexus_autonomous_loop.py")

    print("[*] Verificando compilacion en nodo remoto...")
    stdin, stdout, stderr = ssh.exec_command(f"/home/{user}/Escritorio/NEXUS/venv/bin/python3 -m py_compile {remote_base}/nexus_autonomous_loop.py")
    err = stderr.read().decode()
    if err:
        print(f"[!] Error de compilacion en nodo remoto:\n{err}")
    else:
        print("[+] ¡Despliegue y verificacion exitosos!")

    ssh.close()

if __name__ == "__main__":
    deploy()
