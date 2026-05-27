import paramiko
from scp import SCPClient
import os

def deploy_to_pc2():
    host = os.getenv("SUPER_NEXUS_PC2_IP", "")
    user = os.getenv("SUPER_NEXUS_PC2_USER", "")
    password = os.getenv("SUPER_NEXUS_PC2_PASSWORD", "")
    local_script = os.path.join(os.path.dirname(__file__), "setup_service_pc2.sh")
    remote_script = f"/home/{user}/setup_service_pc2.sh"

    if not host or not user or not password:
        print("ERROR: SUPER_NEXUS_PC2_IP, SUPER_NEXUS_PC2_USER, and SUPER_NEXUS_PC2_PASSWORD must be set in .env")
        return

    try:
        print(f"Connecting to {host}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=password)

        print(f"Uploading script...")
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(local_script, remote_script)

        print(f"Executing script (this may take a while)...")
        command = f"chmod +x {remote_script} && bash {remote_script}"
        stdin, stdout, stderr = ssh.exec_command(command)

        while True:
            line = stdout.readline()
            if not line:
                break
            try:
                print(f"[PC2] {line.strip()}")
            except UnicodeEncodeError:
                print(f"[PC2] {line.encode('ascii', 'ignore').decode().strip()}")

        err = stderr.read().decode()
        if err:
            print(f"[ERROR] {err}")

        ssh.close()
        print("Deployment finished.")

    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    deploy_to_pc2()
