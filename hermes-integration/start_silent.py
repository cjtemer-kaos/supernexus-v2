"""Start SuperNEXUS server hidden (no console window)."""
import subprocess, sys, os, time

python = sys.executable  # python.exe
pythonw = python.replace("python.exe", "pythonw.exe")  # pythonw.exe (no console)

script = os.path.join(os.path.dirname(__file__), "start_server.py")

proc = subprocess.Popen(
    [pythonw, script, "9000"],
    creationflags=subprocess.CREATE_NO_WINDOW,
    cwd=os.path.dirname(__file__),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

print(f"SuperNEXUS started hidden (PID: {proc.pid})")
