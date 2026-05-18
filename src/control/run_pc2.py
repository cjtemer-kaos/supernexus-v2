import paramiko
import sys
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def run_Remote Node_command(command):
    host = os.getenv("SUPER_NEXUS_Remote Node_IP", "")
    user = os.getenv("SUPER_NEXUS_Remote Node_USER", "")
    pw = os.getenv("SUPER_NEXUS_Remote Node_PASSWORD", "")

    if not host or not user:
        return "", "Remote node not configured. Set SUPER_NEXUS_Remote Node_IP and SUPER_NEXUS_Remote Node_USER in .env"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, username=user, password=pw, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command)
        out = stdout.read().decode(errors='ignore')
        err = stderr.read().decode(errors='ignore')
        ssh.close()
        return out, err
    except Exception as e:
        return "", str(e)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "pwd && ls -la"
    out, err = run_Remote Node_command(cmd)
    print("STDOUT:")
    print(out)
    print("STDERR:")
    print(err)
