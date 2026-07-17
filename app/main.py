from flask import Flask, jsonify, redirect, render_template, request, url_for

from app.clients.repository import count_clients, create_client, list_clients, set_client_enabled
from app.connections.service import list_connections
from app.db import init_db


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )

    init_db()

    @app.get("/")
    def dashboard():
        connections = list_connections()
        status_items = [
            {"label": "Server", "value": "Works", "state": "ok"},
            {"label": "AmneziaWG", "value": connections[0].status, "state": "idle"},
            {"label": "Xray", "value": connections[1].status, "state": "idle"},
            {"label": "Clients", "value": str(count_clients()), "state": "idle"},
            {"label": "Traffic today", "value": "0 GB", "state": "idle"},
            {"label": "Backup", "value": "Not created", "state": "idle"},
        ]
        return render_template("dashboard.html", active_page="dashboard", status_items=status_items)

    @app.get("/clients")
    def clients():
        return render_template("clients.html", active_page="clients", clients=list_clients())

    @app.post("/clients")
    def add_client():
        create_client(
            name=request.form.get("name", ""),
            access=request.form.get("access", "recommended"),
        )
        return redirect(url_for("clients"))

    @app.post("/clients/<int:client_id>/enable")
    def enable_client(client_id: int):
        set_client_enabled(client_id, True)
        return redirect(url_for("clients"))

    @app.post("/clients/<int:client_id>/disable")
    def disable_client(client_id: int):
        set_client_enabled(client_id, False)
        return redirect(url_for("clients"))

    @app.get("/connections")
    def connections():
        return render_template(
            "connections.html",
            active_page="connections",
            connections=list_connections(),
        )

    @app.get("/health")
    def health():
        return jsonify(
            {
                "service": "sg-gateway-panel",
                "status": "ok",
            }
        )

    return app


app = create_app()