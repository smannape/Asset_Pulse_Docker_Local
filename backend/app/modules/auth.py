"""JWT token creation/verification and bcrypt password hashing."""

from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY") or secrets.token_urlsafe(48)
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 h

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    user_id: int,
    email: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, str]:
    """Return (encoded_jwt, jti).  jti is stored in user_sessions for revocation."""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "jti": jti,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM), jti


def decode_access_token(token: str) -> dict:
    """Decode and verify JWT.  Raises JWTError if invalid or expired."""
    return jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
