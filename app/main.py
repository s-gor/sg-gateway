from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for

from app.clients.access import build_access_cards
from app.clients.exports import build_awg_config, build_subscription, build_xray_link
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
from app.connections.settings import get_connection_settings, update_connection_settings
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

    @app.get("/clients/<int:client_id>/exports/<kind>")
    def export_client_access(client_id: int, kind: str):
        client = get_client(client_id)
        if client is None:
            abort(404)

        builders = {
            "amneziawg": build_awg_config,
            "xray": build_xray_link,
            "subscription": build_subscription,
        }
        builder = builders.get(kind)
        if builder is None:
            abort(404)

        export = builder(client)
        return Response(
            export.body,
            mimetype=export.media_type,
            headers={"Content-Disposition": f"attachment; filename={export.filename}"},
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
            awg_settings=get_connection_settings("amneziawg"),
            xray_settings=get_connection_settings("xray"),
        )

    @app.post("/connections/amneziawg")
    def update_amneziawg():
        current = get_connection_settings("amneziawg")
        config = dict(current.config)
        config["dns"] = request.form.get("dns", config.get("dns", "1.1.1.1"))
        config["server_public_key"] = request.form.get(
            "server_public_key",
            config.get("server_public_key", "PLACEHOLDER_SERVER_PUBLIC_KEY"),
        )
        update_connection_settings(
            "amneziawg",
            request.form.get("host", current.host),
            int(request.form.get("port", current.port)),
            config,
        )
        return redirect(url_for("connections"))

    @app.post("/connections/xray")
    def update_xray():
        current = get_connection_settings("xray")
        config = dict(current.config)
        config["server_name"] = request.form.get(
            "server_name",
            config.get("server_name", "www.cloudflare.com"),
        )
        config["public_key"] = request.form.get(
            "public_key",
            config.get("public_key", "PLACEHOLDER_REALITY_PUBLIC_KEY"),
        )
        config["short_id"] = request.form.get(
            "short_id",
            config.get("short_id", "PLACEHOLDER_SHORT_ID"),
        )
        update_connection_settings(
            "xray",
            request.form.get("host", current.host),
            int(request.form.get("port", current.port)),
            config,
        )
        return redirect(url_for("connections"))

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