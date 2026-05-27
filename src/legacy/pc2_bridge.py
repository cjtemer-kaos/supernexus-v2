import subprocess
import json
import os
import sys

class PC2Bridge:
    """Puente SSH a nodo remoto (configurable via env vars)"""

    def __init__(self, user=None, ip=None, password=None):
        self.user = user or os.getenv("SUPER_NEXUS_PC2_USER", "")
        self.ip = ip or os.getenv("SUPER_NEXUS_PC2_IP", "")
        self.password = password or os.getenv("SUPER_NEXUS_PC2_PASSWORD", "")
        self.timeout = 10

    def is_configured(self):
        """Check if remote node is configured"""
        return bool(self.ip and self.user)

    def exec_command(self, command):
        """Ejecuta comando en nodo remoto via SSH"""
        if not self.is_configured():
            return {"success": False, "error": "Remote node not configured. Set SUPER_NEXUS_PC2_IP and SUPER_NEXUS_PC2_USER in .env"}

        if self.password:
            ssh_cmd = f"sshpass -p {self.password} ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no {self.user}@{self.ip} '{command}'"
        else:
            ssh_cmd = f"ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no {self.user}@{self.ip} '{command}'"

        try:
            result = subprocess.check_output(
                ssh_cmd,
                shell=True,
                stderr=subprocess.STDOUT,
                timeout=self.timeout,
                text=True
            )
            return {"success": True, "output": result}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout ({self.timeout}s) conectando a {self.ip}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_connection(self):
        """Prueba la conexion al nodo remoto"""
        if not self.is_configured():
            print("⚠️  Remote node not configured. Set SUPER_NEXUS_PC2_IP in .env")
            return False

        print(f"📡 Conectando a nodo remoto ({self.ip})...")
        result = self.exec_command("uname -a && echo '---' && uptime")

        if result["success"]:
            print(f"✅ Conexion OK:\n{result['output']}")
            return True
        else:
            print(f"❌ Error: {result['error']}")
            return False

    def search_gemas(self, pattern="*gem*", min_size="5M"):
        """Busca archivos gemas grandes en nodo remoto"""
        if not self.is_configured():
            return []

        find_cmd = f"find /home/{self.user} -name '{pattern}' -size +{min_size} 2>/dev/null | head -20"
        print(f"\n🔍 Buscando archivos ({min_size}+)...")
        result = self.exec_command(find_cmd)

        if result["success"]:
            if result["output"].strip():
                print(f"✅ Archivos encontrados:\n{result['output']}")
                return result["output"].strip().split('\n')
            else:
                print("⚠️  No se encontraron archivos")
                return []
        else:
            print(f"❌ Error: {result['error']}")
            return []

    def copy_gemas_to_windows(self, remote_path, local_path):
        """Descarga archivo gemas desde nodo remoto"""
        if not self.is_configured():
            print("❌ Remote node not configured")
            return False

        print(f"\n📥 Descargando {remote_path}...")

        if self.password:
            scp_cmd = f"sshpass -p {self.password} scp -o ConnectTimeout=5 {self.user}@{self.ip}:{remote_path} {local_path}"
        else:
            scp_cmd = f"scp -o ConnectTimeout=5 {self.user}@{self.ip}:{remote_path} {local_path}"

        try:
            subprocess.run(scp_cmd, shell=True, check=True, timeout=300)
            print(f"✅ Archivo descargado a: {local_path}")
            return True
        except Exception as e:
            print(f"❌ Error descargando: {str(e)}")
            return False


def main():
    # Configuracion desde variables de entorno
    bridge = PC2Bridge()

    if not bridge.is_configured():
        print("⚠️  Remote node not configured.")
        print("   Set SUPER_NEXUS_PC2_IP and SUPER_NEXUS_PC2_USER in .env")
        print("   (Optional) Set SUPER_NEXUS_PC2_PASSWORD for password auth")
        return

    # 1. Probar conexion
    if not bridge.test_connection():
        print("\n⚠️  No se puede conectar al nodo remoto. Verifica:")
        print("  - El nodo esta encendido y en la red")
        print("  - Usuario y contraseña son correctos")
        print("  - SSH esta habilitado en el nodo remoto")
        return

    # 2. Buscar archivos gemas
    gemas = bridge.search_gemas()

    if gemas:
        print(f"\n📦 Total: {len(gemas)} archivos encontrados")

        # 3. Descargar el primero como ejemplo
        first = gemas[0]
        local_path = os.path.join(os.path.expanduser("~"), "Downloads", os.path.basename(first))
        bridge.copy_gemas_to_windows(first, local_path)


if __name__ == "__main__":
    main()
