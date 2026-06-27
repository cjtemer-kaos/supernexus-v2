import paramiko
import sys
import os

def run_remote(host, user, password, command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=user, password=password, timeout=10)

        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        error = stderr.read().decode()

        client.close()
        return output, error
    except Exception as e:
        return None, str(e)

if __name__ == "__main__":
    h = os.getenv("SUPER_NEXUS_PC2_IP", "")
    u = os.getenv("SUPER_NEXUS_PC2_USER", "")
    p = os.getenv("SUPER_NEXUS_PC2_PASSWORD", "")

    if not h or not u:
        print("FAILED: SUPER_NEXUS_PC2_IP and SUPER_NEXUS_PC2_USER must be set in .env")
        sys.exit(1)

    out, err = run_remote(h, u, p, "sudo journalctl -u openclaw -n 50 --no-pager")
    if out:
        try:
            print(f"SUCCESS:\n{out}")
        except UnicodeEncodeError:
            print(f"SUCCESS:\n{out.encode('ascii', 'ignore').decode()}")
    else:
        print(f"FAILED: {err}")
