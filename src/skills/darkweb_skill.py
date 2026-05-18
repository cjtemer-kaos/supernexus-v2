"""
Dark Web Skill - Tor Browser Control
Navigation and research using Tor Browser
"""

import subprocess
import os
import json
from datetime import datetime

TOR_PATH = os.getenv("TOR_BROWSER_PATH", "")
TOR_PROFILE = os.getenv("TOR_PROFILE_PATH", "")

class DarkWebSkill:
    def __init__(self):
        self.name = "darkweb"
        self.description = "Control Tor Browser para dark web"
        self.tor_path = TOR_PATH
    
    def is_running(self) -> bool:
        """Check if Tor Browser is running"""
        try:
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True
            )
            return "firefox.exe" in result.stdout
        except:
            return False
    
    def start(self) -> str:
        """Start Tor Browser"""
        if self.is_running():
            return "Already running"
        try:
            subprocess.Popen([self.tor_path])
            return "Started Tor Browser"
        except Exception as e:
            return f"Error: {e}"
    
    def info(self) -> dict:
        return {
            "skill": self.name,
            "description": self.description,
            "tor_running": self.is_running()
        }

def is_running() -> bool:
    """Check if Tor Browser is running"""
    try:
        result = subprocess.run(
            ["tasklist"],
            capture_output=True,
            text=True
        )
        return "firefox.exe" in result.stdout
    except:
        return False

def start() -> str:
    """Start Tor Browser"""
    if is_running():
        return "Already running"
    try:
        subprocess.Popen([TOR_PATH])
        return "Started Tor Browser"
    except Exception as e:
        return f"Error: {e}"

def open_url(url: str) -> str:
    """Open URL in Tor Browser"""
    if not is_running():
        start()
    
    try:
        subprocess.run([
            TOR_PATH,
            "-new-tab",
            url
        ])
        return f"Opened: {url}"
    except Exception as e:
        return f"Error: {e}"

def search_darkweb(query: str) -> str:
    """Search on darkweb (using onion search engines)"""
    search_urls = [
        f"http://localhost:8080/search?q={query}",
        f"https://duckduckgogg2xj2aqae3fwgq3q5daxcgit3yd22hlmlkzr2cx3rpxnotid.onion/?q={query}"
    ]
    return "Use open_url() to navigate to onion search engines like:\n- Ahmia\n- DuckDuckGo onion\n- Torch"

def handle(query: str) -> str:
    """Handle darkweb queries"""
    query_lower = query.lower()
    
    if "start" in query_lower or "abrir" in query_lower:
        return start()
    
    if "status" in query_lower:
        return json.dumps({"tor_running": is_running()})
    
    if "search" in query_lower:
        return search_darkweb(query.replace("search", "").replace("buscar", "").strip())
    
    return f"Tor Browser: {'Running' if is_running() else 'Not running'}"