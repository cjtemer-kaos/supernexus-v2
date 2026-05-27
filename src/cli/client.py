import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)

TOKEN_FILE = Path.home() / ".nexus" / "cli_token.json"


def _save_token(token: str, host: str):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps({"token": token, "host": host}))


def _load_token(host: str) -> str | None:
    if TOKEN_FILE.exists():
        try:
            data = json.loads(TOKEN_FILE.read_text())
            if data.get("host") == host:
                return data.get("token")
        except (json.JSONDecodeError, KeyError):
            pass
    return None


class NexusClient:
    def __init__(self, base_url: str = "http://localhost:9000"):
        self.base_url = base_url.rstrip("/")
        self.token = _load_token(self.base_url)

    def set_token(self, token: str):
        self.token = token
        _save_token(token, self.base_url)

    def _request(self, method: str, path: str, data: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"} if data else {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            try:
                err_data = json.loads(err)
                if e.code == 401 and "login" not in path:
                    err_data["_auth_required"] = True
                return err_data
            except json.JSONDecodeError:
                return {"error": err, "_code": e.code}
        except Exception as e:
            return {"error": str(e)}

    def _get(self, path: str) -> dict:
        return self._request("GET", path)

    def _post(self, path: str, data: dict | None = None) -> dict:
        return self._request("POST", path, data)

    def status(self) -> dict:
        return self._get("/api/status")

    def doctor(self) -> dict:
        return self._get("/api/doctor")

    def chat(self, message: str, gem: str = "") -> dict:
        payload = {"message": message}
        if gem:
            payload["gem"] = gem
        return self._post("/api/chat", payload)

    def gemas(self) -> dict:
        return self._get("/api/gems")

    def memory_search(self, query: str, limit: int = 10) -> dict:
        return self._post("/api/memory/search", {"query": query, "limit": limit})

    def memory_stats(self) -> dict:
        return self._get("/api/brain/stats")

    def memory_consolidate(self) -> dict:
        return self._post("/api/memory/dream", {})

    def memory_health(self) -> dict:
        return self._get("/api/memory/health")

    def devloop_run(self, task: str) -> dict:
        return self._post("/api/devloop/run", {"task": task})

    def devloop_status(self) -> dict:
        return self._get("/api/devloop/status")

    def conductor_spawn(self, name: str, goal: str) -> dict:
        return self._post("/api/conductor/spawn", {"name": name, "goal": goal})

    def conductor_list(self) -> dict:
        return self._get("/api/conductor/status")

    def conductor_merge(self, name: str) -> dict:
        return self._post("/api/conductor/merge", {"name": name})

    def conductor_cleanup(self, name: str) -> dict:
        return self._post("/api/conductor/cleanup", {"name": name})

    def skill_list(self) -> dict:
        return self._get("/api/skills/marketplace")

    def skill_install(self, name: str) -> dict:
        return self._post("/api/skills/install", {"name": name})

    def skill_publish(self, name: str) -> dict:
        return self._post("/api/skills/publish", {"name": name})

    def health(self) -> dict:
        return self._get("/api/health")

    def token_usage(self) -> dict:
        return self._get("/api/tokens/usage")

    def agent_loop_run(self, prompt: str) -> dict:
        return self._post("/api/agent-loop/run", {"prompt": prompt})

    def login(self, password: str) -> dict:
        return self._post("/api/auth/login", {"password": password})

    def login_status(self) -> dict:
        return self._get("/api/auth/status")

    def absorb_repo(self, repo_path: str) -> dict:
        return self._post("/api/absorb/repo", {"repo_path": repo_path})

    def absorb_status(self) -> dict:
        return self._get("/api/absorb/status")

    def config_set(self, key: str, value: str) -> dict:
        return self._post("/api/config", {"key": key, "value": value})

    def config_get(self, key: str) -> dict:
        return self._get(f"/api/config/{key}")
