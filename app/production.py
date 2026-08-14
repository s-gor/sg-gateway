"""Compatibility WSGI entrypoint for existing SG-Gateway installations.

Some installed 021 systemd units still launch ``app.production:app``.
Panel-only updates intentionally preserve those units, so this module must stay
available while the canonical entrypoint remains ``app.main:app``.
"""

from app.main import app, create_app

application = app

__all__ = ["app", "application", "create_app"]
