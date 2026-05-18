"""
Streamlabs OBS Skill - Live Streaming Control
Control Streamlabs OBS for live streaming automation
"""

import subprocess
import os
import time
import json

STREAMLABS_PATH = r"C:\Program Files\Streamlabs\Streamlabs OBS\Streamlabs OBS.exe"

class StreamlabsOBSSkill:
    def __init__(self):
        self.name = "streamlabs"
        self.description = "Control Streamlabs OBS para streaming"
        self.path = STREAMLABS_PATH
    
    def is_running(self) -> bool:
        """Check if Streamlabs is running"""
        try:
            result = subprocess.run(
                ["tasklist"], 
                capture_output=True, 
                text=True
            )
            return "Streamlabs OBS" in result.stdout
        except:
            return False
    
    def start(self) -> str:
        """Start streaming"""
        if self.is_running():
            return "Already running"
        try:
            subprocess.Popen([self.path])
            return "Started"
        except Exception as e:
            return f"Error: {e}"
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "running": self.is_running()
        }

def is_streaming() -> bool:
    """Check if Streamlabs is running"""
    try:
        result = subprocess.run(
            ["tasklist"], 
            capture_output=True, 
            text=True
        )
        return "Streamlabs OBS" in result.stdout
    except:
        return False

def start_stream() -> str:
    """Start streaming"""
    if is_streaming():
        return "Already running"
    try:
        subprocess.Popen([STREAMLABS_PATH])
        return "Started"
    except Exception as e:
        return f"Error: {e}"

def stop_stream() -> str:
    """Stop streaming scene"""
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", "Streamlabs OBS.exe"],
            capture_output=True
        )
        return "Stopped" if result.returncode == 0 else "Not running"
    except:
        return "Error"

def handle(query: str) -> str:
    """Handle streaming queries"""
    query_lower = query.lower()
    
    if "start" in query_lower or "iniciar" in query_lower:
        return start_stream()
    
    if "stop" in query_lower:
        return stop_stream()
    
    if "status" in query_lower or "estado" in query_lower:
        return json.dumps({"streaming": is_streaming()})
    
    return f"Status: {is_streaming()}"