"""SuperNEXUS v2 — Silent Launcher (no console windows)"""
import subprocess
import socket
import time
import os
import sys

PROJECT_DIR = r"D:\ias\proyectos\supernexus-v2"
ELECTRON_DIR = os.path.join(PROJECT_DIR, "desktop")
ELECTRON_EXE = os.path.join(ELECTRON_DIR, "node_modules", "electron", "dist", "electron.exe")

# Use system Python (3.13), not Hermes venv (3.11) which lacks dependencies
PYTHON_EXE = r"C:\Users\cjtr\AppData\Local\Programs\Python\Python313\python.exe"

CREATE_NO_WINDOW = 0x08000000
STARTUPINFO = subprocess.STARTUPINFO()
STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
STARTUPINFO.wShowWindow = 0  # SW_HIDE

def server_running():
    try:
        s = socket.create_connection(("localhost", 9000), timeout=2)
        s.close()
        return True
    except:
        return False

if not server_running():
    subprocess.Popen(
        [PYTHON_EXE, "start_server.py", "9000"],
        cwd=PROJECT_DIR,
        creationflags=CREATE_NO_WINDOW,
        startupinfo=STARTUPINFO,
        close_fds=True
    )
    for _ in range(30):
        time.sleep(2)
        if server_running():
            break

subprocess.Popen(
    [ELECTRON_EXE, "."],
    cwd=ELECTRON_DIR,
    creationflags=CREATE_NO_WINDOW,
    startupinfo=STARTUPINFO,
    close_fds=True
)
