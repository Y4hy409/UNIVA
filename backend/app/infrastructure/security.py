"""
CLARIUS Backend - Security Infrastructure

This module handles cryptographic operations including password hashing,
symmetric encryption for credentials, and JSON Web Token (JWT) management.
"""

import time
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import hashlib
import os
import jwt
from uuid import UUID
from app.core.config import settings

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    salt = os.urandom(16)
    db_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2_sha256$100000${salt.hex()}${db_hash.hex()}"


import hmac

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its PBKDF2-HMAC-SHA256 hash."""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 4 or parts[0] != 'pbkdf2_sha256':
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        db_hash = bytes.fromhex(parts[3])
        candidate_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(db_hash, candidate_hash)
    except Exception:
        return False


# Secret encryption context
# If ENCRYPTION_KEY is not set, generate a default fallback or raise error
_fernet: Optional[Fernet] = None

def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.ENCRYPTION_KEY
        if not key:
            # For development, derive a stable key from SECRET_KEY
            import base64
            import hashlib
            derived = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            key = base64.urlsafe_b64encode(derived)
        else:
            if isinstance(key, str):
                key = key.encode()
        _fernet = Fernet(key)
    return _fernet


def encrypt_secret(plain_text: str) -> str:
    """Encrypt a secret string using AES Fernet."""
    f = _get_fernet()
    return f.encrypt(plain_text.encode()).decode()


def decrypt_secret(cipher_text: str) -> str:
    """Decrypt an AES Fernet cipher text."""
    f = _get_fernet()
    return f.decrypt(cipher_text.encode()).decode()


# JWT Authentication tokens
JWT_ALGORITHM = "HS256"

def create_access_token(user_id: UUID, role: str, expires_in_seconds: int = 86400) -> str:
    """Generate a JWT access token for a user."""
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time())
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None
