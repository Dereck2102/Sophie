from __future__ import annotations

import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()
_ph = PasswordHasher()


# ── Password Hashing (Argon2) ──────────────────────────────────────────────


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


# ── JWT Tokens ─────────────────────────────────────────────────────────────


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


# ── MFA / TOTP ─────────────────────────────────────────────────────────────


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=username, issuer_name=settings.MFA_ISSUER
    )


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ── AES-256-GCM Vault Encryption ───────────────────────────────────────────


def _get_vault_key() -> bytes:
    raw = os.getenv("VAULT_SECRET_KEY", "")
    if not raw:
        raise RuntimeError("VAULT_SECRET_KEY environment variable is not set")
    key_bytes = base64.b64decode(raw)
    if len(key_bytes) != 32:
        raise RuntimeError("VAULT_SECRET_KEY must decode to exactly 32 bytes for AES-256")
    return key_bytes


def encrypt_vault(plain_text: str) -> str:
    """Encrypt with AES-256-GCM. Returns base64(nonce + ciphertext)."""
    key = _get_vault_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plain_text.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_vault(cipher_b64: str) -> str:
    """Decrypt AES-256-GCM ciphertext. Expects base64(nonce + ciphertext)."""
    key = _get_vault_key()
    aesgcm = AESGCM(key)
    data = base64.b64decode(cipher_b64)
    nonce, ct = data[:12], data[12:]
    return aesgcm.decrypt(nonce, ct, None).decode()
