"""
signer — Ed25519 signing/verification for .nexus-gema packages.

Pattern (openfang Ed25519 manifest signing): operator can publish a gema
signed with their private key; downstream installs verify against the
known public key. If the cryptography lib isn't installed, signing is a
no-op (logged once) so the package format works degraded.

Wire format inside manifest.json:
    {
      ...,
      "signature": {
        "alg": "ed25519",
        "public_key": "<base64>",
        "sig": "<base64 sig over canonical(manifest excluding signature)>"
      }
    }

Canonicalization: JSON dumps with sort_keys=True, separators=(",", ":")
of the manifest dict WITHOUT the 'signature' field.
"""
from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_CRYPTO_AVAILABLE = False
try:
    from cryptography.hazmat.primitives.asymmetric import ed25519 as _ed
    from cryptography.hazmat.primitives import serialization as _ser
    from cryptography.exceptions import InvalidSignature as _BadSig
    _CRYPTO_AVAILABLE = True
except Exception:
    pass


def crypto_available() -> bool:
    return _CRYPTO_AVAILABLE


def _canonical(manifest: dict) -> bytes:
    payload = {k: v for k, v in manifest.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def generate_keypair(out_dir: Optional[Path] = None) -> Tuple[Path, Path]:
    """Create new Ed25519 keypair, write to disk, return (private, public).
    Private file is mode 0600. Idempotent — refuses if files already exist."""
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography not installed — `pip install cryptography`")
    out_dir = out_dir or (Path.home() / ".nexus" / "keys")
    out_dir.mkdir(parents=True, exist_ok=True)
    priv_p = out_dir / "gema_signing_key.pem"
    pub_p = out_dir / "gema_signing_key.pub"
    if priv_p.exists() or pub_p.exists():
        raise FileExistsError(f"key files already exist at {out_dir}")
    sk = _ed.Ed25519PrivateKey.generate()
    pk = sk.public_key()
    priv_bytes = sk.private_bytes(
        encoding=_ser.Encoding.PEM,
        format=_ser.PrivateFormat.PKCS8,
        encryption_algorithm=_ser.NoEncryption(),
    )
    pub_bytes = pk.public_bytes(
        encoding=_ser.Encoding.PEM, format=_ser.PublicFormat.SubjectPublicKeyInfo,
    )
    from src.security.atomic_io import atomic_write_bytes
    atomic_write_bytes(priv_p, priv_bytes, mode=0o600)
    atomic_write_bytes(pub_p, pub_bytes, mode=0o644)
    return priv_p, pub_p


def sign_manifest(manifest: dict, private_key_path: Path) -> dict:
    """Add signature block to a manifest. Returns new dict (does not mutate)."""
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography not installed")
    sk_pem = Path(private_key_path).read_bytes()
    sk = _ser.load_pem_private_key(sk_pem, password=None)
    if not isinstance(sk, _ed.Ed25519PrivateKey):
        raise ValueError("key is not Ed25519")
    payload = _canonical(manifest)
    sig = sk.sign(payload)
    pub_bytes = sk.public_key().public_bytes(
        encoding=_ser.Encoding.Raw, format=_ser.PublicFormat.Raw,
    )
    out = dict(manifest)
    out["signature"] = {
        "alg": "ed25519",
        "public_key": base64.b64encode(pub_bytes).decode("ascii"),
        "sig": base64.b64encode(sig).decode("ascii"),
    }
    return out


def verify_manifest(manifest: dict, *, trusted_pubkeys_b64: Optional[set] = None,
                    ) -> Tuple[bool, str]:
    """Verify manifest signature. If trusted_pubkeys_b64 provided, also
    require the signing public key to be in that set. Returns (ok, reason).
    """
    if not _CRYPTO_AVAILABLE:
        return False, "cryptography not installed"
    sig_block = manifest.get("signature")
    if not isinstance(sig_block, dict):
        return False, "no signature block"
    if sig_block.get("alg") != "ed25519":
        return False, f"unsupported alg: {sig_block.get('alg')}"
    try:
        pub_b64 = sig_block["public_key"]
        sig_b64 = sig_block["sig"]
        pub_bytes = base64.b64decode(pub_b64)
        sig_bytes = base64.b64decode(sig_b64)
    except Exception as e:
        return False, f"bad base64: {e}"
    if trusted_pubkeys_b64 is not None and pub_b64 not in trusted_pubkeys_b64:
        return False, "signing key not in trusted set"
    try:
        pk = _ed.Ed25519PublicKey.from_public_bytes(pub_bytes)
        pk.verify(sig_bytes, _canonical(manifest))
        return True, "ok"
    except _BadSig:
        return False, "invalid signature"
    except Exception as e:
        return False, f"verify error: {e}"


def verify_gema_package(manifest: dict, gema_bytes: bytes) -> Tuple[bool, str]:
    """Convenience hook called by src.plugins.package.import_gema when
    verify_signature=True. Today: just delegates to verify_manifest with
    no trust pinning. Distribution operators can wrap this and provide
    trusted_pubkeys_b64 from a config file."""
    return verify_manifest(manifest)
