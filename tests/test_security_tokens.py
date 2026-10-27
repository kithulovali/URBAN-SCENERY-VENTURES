import hashlib
import hmac
import json
import time

from core.config import settings
from core.security import _base64url_encode, create_access_token, decode_access_token


def signed_token(header, payload):
    header_part = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_part = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header_part}.{payload_part}.{_base64url_encode(signature)}"


def test_valid_access_token_decodes():
    token = create_access_token({"sub": "user-123"})
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["exp"] > time.time()


def test_access_token_without_expiration_is_rejected():
    token = signed_token({"alg": "HS256", "typ": "JWT"}, {"sub": "user-123"})

    assert decode_access_token(token) is None


def test_expired_access_token_is_rejected():
    token = signed_token(
        {"alg": "HS256", "typ": "JWT"},
        {"sub": "user-123", "exp": int(time.time()) - 60},
    )

    assert decode_access_token(token) is None


def test_access_token_with_unsupported_algorithm_is_rejected():
    token = signed_token(
        {"alg": "none", "typ": "JWT"},
        {"sub": "user-123", "exp": int(time.time()) + 60},
    )

    assert decode_access_token(token) is None


def test_access_token_with_non_numeric_expiration_is_rejected():
    token = signed_token(
        {"alg": "HS256", "typ": "JWT"},
        {"sub": "user-123", "exp": "never"},
    )

    assert decode_access_token(token) is None
