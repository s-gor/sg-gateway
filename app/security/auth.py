from __future__ import annotations

import base64
import hashlib
import hmac
from functools import wraps

from flask import redirect, request, session, url_for

from app.config import load_config


PUBLIC_ENDPOINTS = {
    "login",
    "login_post",
    "health",
    "static",
    "recovery",
    "download_diagnostics",
}


def is_authenticated() -> bool:
    return session.get("authenticated") is True


def _verify_pbkdf2_sha256(password: str, encoded: str) -> bool:
    try:
        scheme, rounds_text, salt_text, digest_text = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
    except (TypeError, ValueError, UnicodeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(actual, expected)


def verify_password(password: str) -> bool:
    config = load_config()
    if config.admin_password_hash:
        return _verify_pbkdf2_sha256(password, config.admin_password_hash)
    expected = config.admin_password
    return hmac.compare_digest(password.encode("utf-8"), expected.encode("utf-8"))


def login_user() -> None:
    session["authenticated"] = True


def logout_user() -> None:
    session.clear()


def require_auth(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if is_authenticated():
            return handler(*args, **kwargs)
        return redirect(url_for("login", next=request.path))

    return wrapper


def should_skip_auth(endpoint: str | None) -> bool:
    if endpoint is None:
        return False
    return endpoint in PUBLIC_ENDPOINTS or endpoint.startswith("static")