import base64
import hashlib
import hmac
import json
import math
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.config import settings
from settings import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


# --- Password Hashing (PBKDF2-HMAC-SHA256) ---
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100000,
    )
    return f"pbkdf2:sha256:100000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        algo_iter, salt, stored_hash = parts
        _, _, iterations_str = algo_iter.split(":")
        iterations = int(iterations_str)
        test_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=iterations,
        )
        return hmac.compare_digest(test_key.hex(), stored_hash)
    except Exception:
        return False


# --- Robust URL-Safe JWT Implementation ---
def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("ascii"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp())})

    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts

        # Accept only the signing algorithm this implementation actually uses.
        header = json.loads(_base64url_decode(header_b64).decode("utf-8"))
        if not isinstance(header, dict) or header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        provided_sig = _base64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        if not isinstance(payload, dict):
            return None

        # Expiration is mandatory; tokens without a valid exp must never authenticate.
        exp = payload.get("exp")
        if isinstance(exp, bool) or not isinstance(exp, (int, float)) or not math.isfinite(exp):
            return None
        if datetime.now(timezone.utc).timestamp() >= exp:
            return None

        return payload
    except Exception:
        return None


# --- FastAPI Auth Dependencies ---
def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from models.users_model import User
    from uuid import UUID

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    user_sub = payload.get("sub")
    if not user_sub:
        return None

    try:
        user_uuid = UUID(user_sub)
        return db.get(User, user_uuid)
    except Exception:
        return None


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from models.users_model import User
    from uuid import UUID

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_sub = payload.get("sub")
    if not user_sub:
        raise credentials_exception

    try:
        user_uuid = UUID(user_sub)
    except Exception:
        raise credentials_exception

    user = db.get(User, user_uuid)
    if not user:
        raise credentials_exception
    return user


def get_current_admin(
    current_user=Depends(get_current_user),
):
    role_val = getattr(getattr(current_user, "role", None), "name", "")
    if str(role_val).strip().upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user
