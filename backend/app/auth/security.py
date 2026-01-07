"""backend/app/auth/security.py

مكوّنات بسيطة للمصادقة بدون اعتمادات خارجية.

يدعم:
- Hashing كلمات المرور (PBKDF2-HMAC-SHA256)
- Token شبيه JWT (HS256) لتجنّب اعتماد مكتبات إضافية.

ملاحظة: في بيئة إنتاج يفضّل استخدام مكتبات قياسية مُدققة (PyJWT/Passlib)
وضبط SECRET قوي جداً.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, Optional


def _b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("utf-8"))


def hash_password(password: str, *, iterations: int = 120_000) -> str:
    """ينتج قيمة قابلة للتخزين في DB."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2$%d$%s$%s" % (iterations, _b64url_encode(salt), _b64url_encode(dk))


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, it_s, salt_s, dk_s = stored.split("$", 3)
        if scheme != "pbkdf2":
            return False
        iterations = int(it_s)
        salt = _b64url_decode(salt_s)
        expected = _b64url_decode(dk_s)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def create_token(payload: Dict[str, Any], secret: str, ttl_seconds: int) -> str:
    header = {"alg": "HS256", "typ": "ATHIR"}
    now = int(time.time())
    body = dict(payload)
    body.setdefault("iat", now)
    body["exp"] = now + int(ttl_seconds)

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body_b64 = _b64url_encode(json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    signing_input = f"{header_b64}.{body_b64}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{header_b64}.{body_b64}.{sig_b64}"


def verify_token(token: str, secret: str) -> Optional[Dict[str, Any]]:
    try:
        header_b64, body_b64, sig_b64 = token.split(".", 2)
        signing_input = f"{header_b64}.{body_b64}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_sig, _b64url_decode(sig_b64)):
            return None
        body = json.loads(_b64url_decode(body_b64).decode("utf-8"))
        if int(body.get("exp", 0)) < int(time.time()):
            return None
        return body
    except Exception:
        return None
