"""Bootstrap: auto-install missing dependencies for SuperNEXUS."""
import subprocess, sys, os, json, time, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent

def _run(cmd, desc, timeout=300):
    print(f"[bootstrap] {desc}...")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
        return True
    except Exception as e:
        print(f"[bootstrap] WARNING: {desc} failed: {e}")
        return False

def check_python_deps():
    req = BASE / "requirements.txt"
    if not req.exists():
        print("[bootstrap] No requirements.txt found, skipping pip install")
        return
    installed = set()
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "list", "--format=json"],
                          capture_output=True, text=True, timeout=30)
        installed = {p["name"].lower() for p in json.loads(r.stdout)}
    except Exception:
        pass
    missing = []
    for line in req.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pkg = line.split(">=")[0].split("==")[0].split("[")[0].strip()
        if pkg.lower() not in installed:
            missing.append(line)
    if missing:
        print(f"[bootstrap] {len(missing)} Python packages missing, installing...")
        _run([sys.executable, "-m", "pip", "install"] + ["-r", str(req)],
             "pip install -r requirements.txt", timeout=300)
    else:
        print(f"[bootstrap] All Python packages satisfied ({len(installed)} installed)")

def check_node_deps():
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not npm or not node:
        print("[bootstrap] Node.js or npm not found, skipping npm deps")
        return
    pkgs = ["agent-cu"]
    for pkg in pkgs:
        if not shutil.which(pkg):
            print(f"[bootstrap] npm package '{pkg}' not found, installing globally...")
            _run([npm, "install", "-g", pkg], f"npm install -g {pkg}", timeout=120)
        else:
            print(f"[bootstrap] npm package '{pkg}' already installed")

def check_ollama_models():
    ollama = shutil.which("ollama")
    if not ollama:
        print("[bootstrap] Ollama not found, skipping model check")
        return
    try:
        r = subprocess.run([ollama, "list"], capture_output=True, text=True, timeout=30)
        existing = {line.split()[0].replace(":latest", "") for line in r.stdout.splitlines()[1:]}
        print(f"[bootstrap] Existing Ollama models: {len(existing)}")
    except Exception as e:
        print(f"[bootstrap] Could not list Ollama models: {e}")
        return
    desired = [
        "nexus-director-v6:latest",           # 4.3GB - Orquestador principal
        "carstenuhlig/omnicoder-2-9b:q4_k_m", # 5.7GB - Coding + agentic (code, engineer)
        "qwen3.5:9b",                          # 6.6GB - Vision (vision-qwen35)
        "deepseek-r1:8b",                      # 5.2GB - Razonamiento (sage, scholar, security)
        "nemotron-3-nano:4b",                  # 2.8GB - Analisis rapido (analyst)
        "nomic-embed-text",                    # 274MB - Embeddings (RAG)
        "moondream:latest",                    # 1.7GB - Vision ligera
        "qwen2.5:0.5b",                       # 397MB - Fallback tiny
    ]
    for model in desired:
        name = model.split(":")[0]
        if name not in existing:
            print(f"[bootstrap] Ollama model '{model}' not found, pulling...")
            _run([ollama, "pull", model], f"ollama pull {model}", timeout=600)
        else:
            print(f"[bootstrap] Ollama model '{model}' already present")

def check_system_tools():
    tools = {"git": "git", "node": "node", "npm": "npm", "ollama": "ollama", "python": "python"}
    for name, cmd in tools.items():
        found = shutil.which(cmd) or shutil.which(cmd + ".exe")
        print(f"[bootstrap] {'[OK]' if found else '[WARN]'} {name}: {found or 'not found'}")

def bootstrap(quick=False):
    print("=" * 50)
    print(f"[bootstrap] SuperNEXUS Bootstrapper")
    print("=" * 50)
    check_system_tools()
    check_python_deps()
    if not quick:
        check_ollama_models()
    check_node_deps()
    print("[bootstrap] Bootstrap complete")

if __name__ == "__main__":
    bootstrap("--quick" in sys.argv)
