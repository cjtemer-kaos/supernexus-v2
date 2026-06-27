import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from typing import Any
from pathlib import Path
from src.core import nexus_config

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
    def __init__(self, base_url: str = nexus_config.get_nexus_url()):
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
            with urllib.request.urlopen(req, timeout=90) as resp:
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

    def login(self, username: str, password: str) -> dict:
        return self._post("/api/auth/login", {"username": username, "password": password})

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

    # --- Brain (cerebro.db) ---
    def brain_stats(self) -> dict:
        return self._get("/api/brain/stats")

    def brain_knowledge(self) -> dict:
        return self._get("/api/brain/knowledge")

    def brain_learn(self, content: str, category: str = "") -> dict:
        payload: dict[str, Any] = {"content": content}
        if category:
            payload["category"] = category
        return self._post("/api/brain/learn", payload)

    def brain_recall(self, query: str) -> dict:
        return self._get(f"/api/brain/prompt?context={urllib.parse.quote(query)}")

    def brain_export(self) -> dict:
        return self._get("/api/brain/export")

    # --- Hive (message_board) ---
    def hive_status(self) -> dict:
        return self._get("/api/protocols/status")

    def hive_send(self, target: str, content: str, channel: str = "general") -> dict:
        return self._post("/api/protocols/acp/send", {
            "target": target, "content": content, "channel": channel,
        })

    # --- System ---
    def system_stats(self) -> dict:
        return self._get("/api/system/stats")

    def system_safe(self) -> dict:
        return self._get("/api/system/safe")

    # --- Auth ---
    def auth_status(self) -> dict:
        return self._get("/api/auth/status")

    # --- New endpoints wired in this campaign (commits 7..48) ---
    def chat_session(self, message: str, session_id: str, gem: str = "") -> dict:
        """Chat with explicit session_id (for budget/logs/scratchpad tracking)."""
        payload: dict[str, Any] = {"message": message, "session_id": session_id}
        if gem:
            payload["gem"] = gem
        return self._post("/api/chat", payload)

    def slash_list(self) -> dict:
        return self._get("/api/slash")

    def slash_exec(self, raw: str, session_id: str = "") -> dict:
        body: dict[str, Any] = {"raw": raw}
        if session_id:
            body["session_id"] = session_id
        return self._post("/api/slash", body)

    def sessions_catalog(self) -> dict:
        return self._get("/api/sessions/catalog")

    def session_attach(self, session_id: str) -> dict:
        return self._post(f"/api/sessions/{session_id}/attach", {})

    def session_logs(self, session_id: str, tail: int = 0) -> dict:
        q = f"?tail={tail}" if tail else ""
        return self._get(f"/api/sessions/{session_id}/logs{q}")

    def session_budget(self, session_id: str) -> dict:
        return self._get(f"/api/sessions/{session_id}/budget")

    def session_scratchpad_read(self, session_id: str) -> dict:
        return self._get(f"/api/sessions/{session_id}/scratchpad")

    def session_scratchpad_write(self, session_id: str, content: str = "",
                                  append: str = "", clear: bool = False) -> dict:
        body: dict[str, Any] = {}
        if clear:
            body["clear"] = True
        elif append:
            body["append"] = append
        else:
            body["content"] = content
        return self._post(f"/api/sessions/{session_id}/scratchpad", body)

    def budget_all(self) -> dict:
        return self._get("/api/budget/all")

    def cookbook_scan(self) -> dict:
        return self._get("/api/cookbook/scan")

    def sbom(self) -> dict:
        return self._get("/api/sbom")

    def caps_audit(self) -> dict:
        return self._get("/api/v3/capabilities/audit")

    def mcp_health(self, restart: bool = False) -> dict:
        return self._get(f"/api/mcp/health{'?restart=1' if restart else ''}")

    def workers_stalled(self, threshold_minutes: int = 30) -> dict:
        return self._get(f"/api/workers/stalled?threshold_minutes={threshold_minutes}")

    def dmn_stats(self) -> dict:
        return self._get("/api/dmn/stats")

    def dmn_tick(self) -> dict:
        return self._post("/api/dmn/tick", {})

    def voice_gate_stats(self) -> dict:
        return self._get("/api/voice/gate/stats")

    def events_stats(self) -> dict:
        return self._get("/api/events/stats")

    def setup_preflight(self) -> dict:
        return self._get("/api/setup/preflight")

    def setup_state(self) -> dict:
        return self._get("/api/setup/state")

    def a2a_card(self) -> dict:
        return self._get("/.well-known/agent.json")
