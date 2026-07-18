from __future__ import annotations

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


def verify_password(password: str) -> bool:
    expected = load_config().admin_password
    return hmac.compare_digest(password, expected)


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