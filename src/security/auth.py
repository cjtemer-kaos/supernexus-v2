"""
AuthManager - Autenticacion por cuenta y contrasena para SuperNEXUS v2

- Primer uso: setup interactivo crea cuenta admin
- Login: username + password -> token JWT-like
- Middleware: protege todos los endpoints excepto /api/auth/*
- Password hashing: PBKDF2-HMAC-SHA256 con salt aleatorio
- Tokens: HMAC-SHA256 con expiracion configurable
- Persistencia: SQLite en ~/.nexus/brain/auth.db
"""

import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nexus-auth")

DB_PATH = Path.home() / ".nexus" / "brain" / "auth.db"
SECRET_PATH = Path.home() / ".nexus" / "brain" / "token_secret.key"

def _load_or_create_token_secret() -> str:
    """Carga o crea un token secret persistente en disco"""
    SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SECRET_PATH.exists():
        return SECRET_PATH.read_text(encoding="utf-8").strip()
    secret = secrets.token_hex(32)
    SECRET_PATH.write_text(secret, encoding="utf-8")
    os.chmod(str(SECRET_PATH), 0o600)
    return secret

TOKEN_SECRET = os.environ.get("SUPER_NEXUS_TOKEN_SECRET", _load_or_create_token_secret())
TOKEN_EXPIRY_SECONDS = int(os.environ.get("SUPER_NEXUS_TOKEN_EXPIRY", 86400))  # 24h
MAX_LOGIN_ATTEMPTS = int(os.environ.get("SUPER_NEXUS_MAX_LOGIN_ATTEMPTS", 5))
LOCKOUT_WINDOW_SECONDS = int(os.environ.get("SUPER_NEXUS_LOCKOUT_WINDOW", 900))  # 15 min


@dataclass
class User:
    username: str
    role: str  # admin, user, readonly
    created_at: str
    last_login: str = ""
    is_active: bool = True


@dataclass
class AuthToken:
    token: str
    username: str
    role: str
    expires_at: float
    created_at: float


class PasswordHasher:
    """PBKDF2-HMAC-SHA256 password hashing"""

    ITERATIONS = 260_000  # OWASP 2024 recommendation
    SALT_LENGTH = 32

    @classmethod
    def hash_password(cls, password: str) -> str:
        salt = secrets.token_hex(cls.SALT_LENGTH)
        hash_bytes = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            cls.ITERATIONS,
        )
        return f"{cls.ITERATIONS}${salt}${hash_bytes.hex()}"

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        try:
            iterations, salt, hash_hex = stored_hash.split("$", 2)
            hash_bytes = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            )
            return hmac.compare_digest(hash_bytes.hex(), hash_hex)
        except (ValueError, AttributeError):
            return False


class TokenManager:
    """Genera y valida tokens de sesion"""

    @classmethod
    def generate_token(cls, username: str, role: str) -> AuthToken:
        now = time.time()
        payload = f"{username}:{role}:{now}:{secrets.token_hex(16)}"
        signature = hmac.new(
            TOKEN_SECRET.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        token = f"{payload}:{signature}"
        return AuthToken(
            token=token,
            username=username,
            role=role,
            expires_at=now + TOKEN_EXPIRY_SECONDS,
            created_at=now,
        )

    @classmethod
    def validate_token(cls, token: str) -> Optional[AuthToken]:
        try:
            parts = token.split(":")
            if len(parts) != 5:
                return None

            username, role, timestamp, nonce, signature = parts
            payload = f"{username}:{role}:{timestamp}:{nonce}"

            expected_sig = hmac.new(
                TOKEN_SECRET.encode(),
                payload.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_sig):
                return None

            expires_at = float(timestamp) + TOKEN_EXPIRY_SECONDS
            if time.time() > expires_at:
                return None

            return AuthToken(
                token=token,
                username=username,
                role=role,
                expires_at=expires_at,
                created_at=float(timestamp),
            )
        except (ValueError, IndexError):
            return None


class AuthManager:
    """Gestiona usuarios, login y tokens"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self._in_memory = str(self.db_path) == ":memory:"
        if not self._in_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._mem_conn: Optional[sqlite3.Connection] = None
        self._hasher = PasswordHasher()
        self._token_mgr = TokenManager()
        self._active_tokens: Dict[str, AuthToken] = {}
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._in_memory:
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:")
                self._mem_conn.row_factory = sqlite3.Row
            return self._mem_conn
        conn = sqlite3.connect(str(self.db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _release_conn(self, conn: sqlite3.Connection):
        if not self._in_memory:
            conn.close()

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        if not self._in_memory:
            c.execute("PRAGMA journal_mode=WAL")
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL,
            last_login TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ip TEXT,
            timestamp TEXT NOT NULL,
            success INTEGER
        )""")
        conn.commit()
        self._release_conn(conn)

    def has_users(self) -> bool:
        """Verifica si ya hay cuentas creadas"""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        self._release_conn(conn)
        return count > 0

    def create_user(self, username: str, password: str, role: str = "user") -> Tuple[bool, str]:
        """Crea un nuevo usuario"""
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters"
        if len(username) > 50:
            return False, "Username too long (max 50 chars)"
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters"
        if len(password) > 128:
            return False, "Password too long (max 128 chars)"
        if role not in ("admin", "user", "readonly"):
            return False, "Invalid role"

        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("SELECT username FROM users WHERE username = ?", (username,))
            if c.fetchone():
                return False, "Username already exists"

            password_hash = self._hasher.hash_password(password)
            c.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, time.strftime("%Y-%m-%dT%H:%M:%S")),
            )
            conn.commit()
            logger.info(f"User created: {username} (role: {role})")
            return True, "User created successfully"
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False, f"Error: {e}"
        finally:
            self._release_conn(conn)

    def login(self, username: str, password: str, ip: str = "unknown") -> Tuple[bool, dict]:
        """Autentica usuario y devuelve token"""
        locked, failed_count = self._is_locked_out(username)
        if locked:
            self._log_attempt(username, ip, False)
            remaining = LOCKOUT_WINDOW_SECONDS - (
                time.time() - self._get_last_attempt_time(username)
            )
            return False, {
                "error": f"Account locked due to {failed_count} failed attempts. Try again in {int(remaining)}s",
                "locked": True,
                "retry_after": int(remaining),
            }

        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute(
                "SELECT password_hash, role, is_active FROM users WHERE username = ?",
                (username,),
            )
            row = c.fetchone()

            if not row:
                self._log_attempt(username, ip, False)
                return False, {"error": "Invalid credentials"}

            if not row["is_active"]:
                return False, {"error": "Account is disabled"}

            if not self._hasher.verify_password(password, row["password_hash"]):
                self._log_attempt(username, ip, False)
                new_failed = failed_count + 1
                remaining_attempts = MAX_LOGIN_ATTEMPTS - new_failed
                if remaining_attempts <= 0:
                    return False, {
                        "error": f"Account locked. Try again in {LOCKOUT_WINDOW_SECONDS}s",
                        "locked": True,
                    }
                return False, {
                    "error": "Invalid credentials",
                    "remaining_attempts": remaining_attempts,
                }

            # Update last login
            c.execute(
                "UPDATE users SET last_login = ? WHERE username = ?",
                (time.strftime("%Y-%m-%dT%H:%M:%S"), username),
            )
            conn.commit()
            self._log_attempt(username, ip, True)

            # Generate token
            token = self._token_mgr.generate_token(username, row["role"])
            self._active_tokens[token.token] = token

            return True, {
                "token": token.token,
                "username": username,
                "role": row["role"],
                "expires_at": token.expires_at,
            }
        finally:
            self._release_conn(conn)

    def _get_last_attempt_time(self, username: str) -> float:
        """Obtiene el timestamp del ultimo intento fallido"""
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute(
                "SELECT timestamp FROM login_attempts WHERE username = ? AND success = 0 ORDER BY id DESC LIMIT 1",
                (username,),
            )
            row = c.fetchone()
            if row:
                try:
                    return time.mktime(time.strptime(row[0], "%Y-%m-%dT%H:%M:%S"))
                except ValueError:
                    return 0
            return 0
        finally:
            self._release_conn(conn)

    def validate_token(self, token: str) -> Optional[User]:
        """Valida token y devuelve info del usuario"""
        auth_token = self._token_mgr.validate_token(token)
        if not auth_token:
            return None

        if token not in self._active_tokens:
            return None

        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute(
                "SELECT username, role, created_at, last_login, is_active FROM users WHERE username = ?",
                (auth_token.username,),
            )
            row = c.fetchone()
            if not row or not row["is_active"]:
                return None
            return User(
                username=row["username"],
                role=row["role"],
                created_at=row["created_at"],
                last_login=row["last_login"],
                is_active=bool(row["is_active"]),
            )
        finally:
            self._release_conn(conn)

    def logout(self, token: str) -> bool:
        """Invalida un token"""
        if token in self._active_tokens:
            del self._active_tokens[token]
            return True
        return False

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Cambia la contrasena de un usuario"""
        if len(new_password) < 6:
            return False, "New password must be at least 6 characters"

        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            if not row:
                return False, "User not found"

            if not self._hasher.verify_password(old_password, row["password_hash"]):
                return False, "Current password is incorrect"

            new_hash = self._hasher.hash_password(new_password)
            c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
            conn.commit()
            return True, "Password changed successfully"
        finally:
            self._release_conn(conn)

    def list_users(self) -> List[Dict]:
        """Lista todos los usuarios (sin password hash)"""
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("SELECT username, role, created_at, last_login, is_active FROM users")
            return [dict(r) for r in c.fetchall()]
        finally:
            self._release_conn(conn)

    def delete_user(self, username: str, admin_username: str) -> Tuple[bool, str]:
        """Elimina un usuario (solo admin)"""
        conn = self._get_conn()
        c = conn.cursor()
        try:
            c.execute("SELECT role FROM users WHERE username = ?", (admin_username,))
            row = c.fetchone()
            if not row or row["role"] != "admin":
                return False, "Only admins can delete users"

            c.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            if c.rowcount == 0:
                return False, "User not found"
            return True, "User deleted"
        finally:
            self._release_conn(conn)

    def _log_attempt(self, username: str, ip: str, success: bool):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO login_attempts (username, ip, timestamp, success) VALUES (?, ?, ?, ?)",
            (username, ip, time.strftime("%Y-%m-%dT%H:%M:%S"), 1 if success else 0),
        )
        conn.commit()
        self._release_conn(conn)

    def _is_locked_out(self, username: str) -> Tuple[bool, int]:
        """Verifica si una cuenta esta bloqueada por muchos intentos fallidos"""
        conn = self._get_conn()
        c = conn.cursor()
        try:
            cutoff = time.time() - LOCKOUT_WINDOW_SECONDS
            c.execute(
                "SELECT COUNT(*) FROM login_attempts WHERE username = ? AND success = 0 AND timestamp > ?",
                (username, time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(cutoff))),
            )
            failed = c.fetchone()[0]
            if failed >= MAX_LOGIN_ATTEMPTS:
                return True, failed
            return False, failed
        finally:
            self._release_conn(conn)

    def get_login_attempts(self, username: str = None, limit: int = 100) -> List[Dict]:
        """Obtiene intentos de login"""
        conn = self._get_conn()
        c = conn.cursor()
        try:
            if username:
                c.execute(
                    "SELECT * FROM login_attempts WHERE username = ? ORDER BY id DESC LIMIT ?",
                    (username, limit),
                )
            else:
                c.execute("SELECT * FROM login_attempts ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(r) for r in c.fetchall()]
        finally:
            self._release_conn(conn)

    def get_status(self) -> Dict:
        return {
            "has_users": self.has_users(),
            "active_tokens": len(self._active_tokens),
            "token_expiry_seconds": TOKEN_EXPIRY_SECONDS,
        }
