from __future__ import annotations

import hmac
import secrets

from flask import abort, request, session


CSRF_SESSION_KEY = "csrf_token"


def get_csrf_token() -> str:
    token = session.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def validate_csrf() -> None:
    expected = session.get(CSRF_SESSION_KEY)
    provided = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not expected or not provided or not hmac.compare_digest(str(expected), str(provided)):
        abort(400)
