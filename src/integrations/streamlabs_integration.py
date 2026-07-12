"""
Streamlabs Integration — OAuth2 + Socket API + Alerts

Provides:
  - OAuth2 authorization flow (one-time setup)
  - Real-time event streaming via Socket.IO (donations, subs, follows)
  - Alert control (send test, skip, mute)
  - Donation history

Activation:
  STREAMLABS_CLIENT_ID      app client_id (required)
  STREAMLABS_CLIENT_SECRET  app client_secret (required)
  STREAMLABS_ACCESS_TOKEN   access_token (auto-obtained after OAuth)
  STREAMLABS_SOCKET_TOKEN   socket_token (auto-fetched)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import webbrowser
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode, parse_qs, urlparse

import aiohttp

logger = logging.getLogger("nexus.streamlabs")

REDIRECT_URI = "http://localhost:19876/callback"
SCOPES = "donations.create donations.read alerts.create alerts.write socket.token"

TOKEN_FILE = Path(__file__).parent.parent.parent / ".streamlabs_tokens.json"


class StreamlabsAuth:
    """OAuth2 flow for Streamlabs API."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.socket_token: Optional[str] = None
        self._load_tokens()

    def _load_tokens(self):
        """Load saved tokens from disk."""
        if TOKEN_FILE.exists():
            try:
                data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.socket_token = data.get("socket_token")
                logger.info("Loaded Streamlabs tokens from disk")
            except Exception as e:
                logger.warning(f"Failed to load tokens: {e}")

    def _save_tokens(self):
        """Save tokens to disk."""
        data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "socket_token": self.socket_token,
            "saved_at": time.time(),
        }
        TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Saved Streamlabs tokens to disk")

    def get_authorize_url(self) -> str:
        """Generate the OAuth2 authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
        }
        return f"https://streamlabs.com/api/v2.0/authorize?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Dict:
        """Exchange authorization code for access_token."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": REDIRECT_URI,
                "code": code,
            }
            async with session.post(
                "https://streamlabs.com/api/v2.0/token",
                json=payload,
                headers={"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"},
            ) as resp:
                data = await resp.json()
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    self.refresh_token = data.get("refresh_token")
                    self._save_tokens()
                    return {"success": True, "access_token": self.access_token[:20] + "..."}
                return {"success": False, "error": data}

    async def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh_token."""
        if not self.refresh_token:
            return False
        async with aiohttp.ClientSession() as session:
            payload = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": REDIRECT_URI,
                "refresh_token": self.refresh_token,
            }
            async with session.post(
                "https://streamlabs.com/api/v2.0/token",
                json=payload,
                headers={"Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest"},
            ) as resp:
                data = await resp.json()
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    self.refresh_token = data.get("refresh_token", self.refresh_token)
                    self._save_tokens()
                    return True
                return False

    async def fetch_socket_token(self) -> Optional[str]:
        """Fetch the socket token for real-time events."""
        if not self.access_token:
            return None
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://streamlabs.com/api/v2.0/socket/token",
                headers={"Authorization": f"Bearer {self.access_token}", "X-Requested-With": "XMLHttpRequest"},
            ) as resp:
                data = await resp.json()
                if "socket_token" in data:
                    self.socket_token = data["socket_token"]
                    self._save_tokens()
                    return self.socket_token
                logger.warning(f"Failed to fetch socket token: {data}")
                return None

    @property
    def is_authenticated(self) -> bool:
        return self.access_token is not None

    def headers(self) -> Dict[str, str]:
        """Authorization headers for API calls."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        }


class StreamlabsAPI:
    """Streamlabs REST API client."""

    BASE = "https://streamlabs.com/api/v2.0"

    def __init__(self, auth: StreamlabsAuth):
        self.auth = auth

    async def get_donations(self, limit: int = 10) -> List[Dict]:
        """Fetch recent donations."""
        if not self.auth.is_authenticated:
            return []
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE}/donations",
                params={"limit": limit},
                headers=self.auth.headers(),
            ) as resp:
                data = await resp.json()
                return data if isinstance(data, list) else data.get("data", [])

    async def send_alert(self, alert_type: str, message: str = "", amount: float = 0) -> Dict:
        """Send a test alert."""
        if not self.auth.is_authenticated:
            return {"error": "Not authenticated"}
        payload = {
            "type": alert_type,
            "message": message,
            "amount": amount,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE}/alerts",
                json=payload,
                headers=self.auth.headers(),
            ) as resp:
                return await resp.json()

    async def skip_alert(self) -> Dict:
        """Skip the current alert."""
        if not self.auth.is_authenticated:
            return {"error": "Not authenticated"}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE}/alerts/skip",
                headers=self.auth.headers(),
            ) as resp:
                return await resp.json()

    async def get_user(self) -> Dict:
        """Get authenticated user info."""
        if not self.auth.is_authenticated:
            return {"error": "Not authenticated"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE}/user",
                headers=self.auth.headers(),
            ) as resp:
                return await resp.json()


class StreamlabsSocket:
    """Real-time event listener via Socket.IO."""

    def __init__(self, socket_token: str):
        self.socket_token = socket_token
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def on(self, event_type: str, handler: Callable):
        """Register an event handler.

        event_types: 'donation', 'follow', 'subscription', 'superchat', 'membership'
        """
        self._handlers.setdefault(event_type, []).append(handler)

    async def connect(self):
        """Connect to Streamlabs socket and listen for events."""
        try:
            import socketio
        except ImportError:
            logger.error("python-socketio required: pip install python-socketio")
            return

        sio = socketio.AsyncClient(logger=False, engineio_logger=False)

        @sio.event
        async def connect():
            logger.info("Connected to Streamlabs socket")

        @sio.event
        async def disconnect():
            logger.info("Disconnected from Streamlabs socket")

        @sio.on("event")
        async def on_event(data):
            event_type = data.get("type", "unknown")
            event_for = data.get("for", "")
            messages = data.get("message", [])

            logger.info(f"Streamlabs event: {event_type} (for={event_for})")

            handlers = self._handlers.get(event_type, [])
            for handler in handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(messages, event_for)
                    else:
                        handler(messages, event_for)
                except Exception as e:
                    logger.error(f"Handler error for {event_type}: {e}")

        try:
            url = f"https://sockets.streamlabs.com?token={self.socket_token}"
            await sio.connect(url, transports=["websocket"])
            self._running = True
            await sio.wait()
        except Exception as e:
            logger.error(f"Socket connection failed: {e}")

    def stop(self):
        self._running = False


class StreamlabsIntegration:
    """Unified Streamlabs integration for NEXUS."""

    def __init__(self):
        client_id = os.environ.get("STREAMLABS_CLIENT_ID", "")
        client_secret = os.environ.get("STREAMLABS_CLIENT_SECRET", "")

        self.auth = StreamlabsAuth(client_id, client_secret) if client_id else None
        self.api = StreamlabsAPI(self.auth) if self.auth else None
        self.socket: Optional[StreamlabsSocket] = None
        self._event_log: List[Dict] = []

    @property
    def available(self) -> bool:
        return self.auth is not None and self.auth.is_authenticated

    async def start_oauth_flow(self) -> Dict:
        """Start the OAuth authorization flow."""
        if not self.auth:
            return {"error": "STREAMLABS_CLIENT_ID not configured"}
        url = self.auth.get_authorize_url()
        webbrowser.open(url)
        return {"authorize_url": url, "status": "opened_in_browser"}

    async def complete_oauth(self, code: str) -> Dict:
        """Complete OAuth with the authorization code."""
        if not self.auth:
            return {"error": "Not configured"}
        result = await self.auth.exchange_code(code)
        if result.get("success"):
            socket_token = await self.auth.fetch_socket_token()
            result["socket_token"] = socket_token is not None
        return result

    async def start_socket(self):
        """Start the real-time event listener."""
        if not self.auth or not self.auth.is_authenticated:
            logger.warning("Cannot start socket: not authenticated")
            return

        if not self.auth.socket_token:
            await self.auth.fetch_socket_token()

        if not self.auth.socket_token:
            logger.warning("No socket token available")
            return

        self.socket = StreamlabsSocket(self.auth.socket_token)

        # Default handlers that log events
        def _log_event(messages, event_for):
            for msg in messages if isinstance(messages, list) else [messages]:
                entry = {
                    "type": "streamlabs_event",
                    "for": event_for,
                    "data": msg if isinstance(msg, dict) else {"text": str(msg)},
                    "timestamp": time.time(),
                }
                self._event_log.append(entry)
                if len(self._event_log) > 100:
                    self._event_log = self._event_log[-100:]

        self.socket.on("donation", _log_event)
        self.socket.on("follow", _log_event)
        self.socket.on("subscription", _log_event)
        self.socket.on("superchat", _log_event)
        self.socket.on("membership", _log_event)

        asyncio.create_task(self.socket.connect())

    def get_recent_events(self, limit: int = 10) -> List[Dict]:
        return self._event_log[-limit:]

    async def health_check(self) -> Dict:
        """Check Streamlabs integration status."""
        status = {
            "configured": self.auth is not None,
            "authenticated": self.available,
            "socket_connected": self.socket._running if self.socket else False,
            "events_received": len(self._event_log),
        }
        if self.available and self.api:
            try:
                user = await self.api.get_user()
                status["user"] = user.get("username", "unknown")
            except Exception:
                status["user"] = "error"
        return status


_integration: Optional[StreamlabsIntegration] = None


def get_streamlabs() -> StreamlabsIntegration:
    global _integration
    if _integration is None:
        _integration = StreamlabsIntegration()
    return _integration
