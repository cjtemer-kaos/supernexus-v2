"""Ensure opencode.json has the zen provider configured, and persist API key for server."""
import json, os, pathlib, sys

CONFIG = pathlib.Path(os.path.expanduser("~")) / ".config" / "opencode" / "opencode.json"
NEXUS_HOME = pathlib.Path(os.environ.get("NEXUS_HOME", str(pathlib.Path.home() / ".nexus")))
ZEN_KEY = "sk-34Oiz7pgZl8Wdpg60zr0I8ckowQ4gULfFXpfYDqEsgu6mV3Ox0cI5eA0EuXe5O8A"

# 1) Ensure opencode.json has zen provider
if CONFIG.exists():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if "zen" not in data.setdefault("provider", {}):
        data["provider"]["zen"] = {
            "npm": "@ai-sdk/openai-compatible",
            "name": "OpenCode Zen (free)",
            "options": {
                "baseURL": "https://opencode.ai/zen",
                "apiKey": ZEN_KEY,
            },
            "models": {
                "deepseek-v4-flash-free": {
                    "name": "DeepSeek V4 Flash Free",
                    "limit": {"context": 131072, "output": 8192},
                },
                "nemotron-3-super-free": {
                    "name": "Nemotron 3 Super Free",
                    "limit": {"context": 32768, "output": 4096},
                },
                "big-pickle": {
                    "name": "Big Pickle (stealth model)",
                    "limit": {"context": 32768, "output": 4096},
                },
            },
        }
        if not data.get("model", "").startswith("zen/"):
            data["model"] = "zen/deepseek-v4-flash-free"
        CONFIG.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[ensure_zen] zen provider added to {CONFIG.name}")

# 2) Set env var for server process
os.environ["OPENCODE_API_KEY"] = ZEN_KEY

# 3) Persist to cloud_providers.json so server loads it on startup
cp_path = NEXUS_HOME / "cloud_providers.json"
items = []
if cp_path.exists():
    try:
        items = json.loads(cp_path.read_text(encoding="utf-8"))
    except Exception:
        items = []
found = False
for it in items:
    if it.get("provider_type") == "zen" or "zen" in it.get("id", ""):
        it["api_key"] = ZEN_KEY
        it["base_url"] = "https://api.opencode.ai/zen/v1"
        found = True
        break
if not found:
    items.append({
        "id": f"zen-{int(__import__('time').time()*1000)}",
        "name": "OpenCode Zen",
        "base_url": "https://api.opencode.ai/zen/v1",
        "api_key": ZEN_KEY,
        "provider_type": "openai",
        "free": True,
        "enabled": True,
        "models": [],
    })
cp_path.parent.mkdir(parents=True, exist_ok=True)
cp_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[ensure_zen] API key persisted to {cp_path}")
print(f"[ensure_zen] OPENCODE_API_KEY env var set")
