from flask import Flask, abort, jsonify, redirect, render_template, request, url_for

from app.clients.access import build_access_cards
from app.clients.repository import (
    count_clients,
    create_client,
    delete_client,
    get_client,
    list_clients,
    set_client_enabled,
)
from app.config import load_config
from app.connections.service import list_connections
from app.db import init_db
from app.maintenance.service import collect_diagnostics


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
        client_id = create_client(
            name=request.form.get("name", ""),
            access=request.form.get("access", "recommended"),
        )
        if client_id:
            return redirect(url_for("client_detail", client_id=client_id))
        return redirect(url_for("clients"))

    @app.get("/clients/<int:client_id>")
    def client_detail(client_id: int):
        client = get_client(client_id)
        if client is None:
            abort(404)
        return render_template(
            "client_detail.html",
            active_page="clients",
            client=client,
            access_cards=build_access_cards(client),
        )

    @app.post("/clients/<int:client_id>/enable")
    def enable_client(client_id: int):
        set_client_enabled(client_id, True)
        return redirect(request.referrer or url_for("clients"))

    @app.post("/clients/<int:client_id>/disable")
    def disable_client(client_id: int):
        set_client_enabled(client_id, False)
        return redirect(request.referrer or url_for("clients"))

    @app.post("/clients/<int:client_id>/delete")
    def remove_client(client_id: int):
        delete_client(client_id)
        return redirect(url_for("clients"))

    @app.get("/connections")
    def connections():
        return render_template(
            "connections.html",
            active_page="connections",
            connections=list_connections(),
        )

    @app.get("/maintenance")
    def maintenance():
        return render_template(
            "maintenance.html",
            active_page="maintenance",
            diagnostics=collect_diagnostics(),
        )

    @app.get("/api/status")
    def api_status():
        config = load_config()
        return jsonify(
            {
                "service": "sg-gateway-panel",
                "status": "ok",
                "environment": config.environment,
                "clients": count_clients(),
                "connections": [
                    {
                        "name": connection.name,
                        "status": connection.status,
                        "clients": connection.clients,
                    }
                    for connection in list_connections()
                ],
            }
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