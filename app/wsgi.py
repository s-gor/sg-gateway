"""Production WSGI composition for SG-Gateway 0.1.0-022.05+."""
from __future__ import annotations

from app.main import create_app as create_core_app
from app.clients.sg_subscription_http import register_sg_subscription


def create_app():
    app = create_core_app()
    register_sg_subscription(app)
    return app


app = create_app()
