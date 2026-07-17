from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_file, url_for

from app.clients.access import build_access_cards
from app.clients.exports import build_awg_config, build_subscription, build_xray_link
from app.clients.qr import build_qr_svg
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
from app.help.content import get_topic, list_topics
from app.maintenance.backups import create_backup, get_backup, list_backups, restore_backup
from app.maintenance.diagnostics import build_diagnostic_report, build_diagnostic_report_json
from app.maintenance.health import collect_health_checks, health_summary
from app.maintenance.operations import list_operations
from app.maintenance.service import collect_diagnostics
from app.security.auth import (
    is_authenticated,
    login_user,
    logout_user,
    should_skip_auth,
    verify_password,
)
from app.security.csrf import get_csrf_token, validate_csrf
from app.version import get_release_manifest, get_version


CSRF_EXEMPT_ENDPOINTS = {"login_post"}


def create_app() -> Flask:
    config = load_config()
    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )
    app.secret_key = config.secret_key

    init_db()

    @app.before_request
    def protect_panel():
        if should_skip_auth(request.endpoint):
            return None
        if not is_authenticated():
            return redirect(url_for("login", next=request.path))
        if request.method == "POST" and request.endpoint not in CSRF_EXEMPT_ENDPOINTS:
            validate_csrf()
        return None

    @app.context_processor
    def inject_globals():
        return {
            "app_version": get_version(),
            "is_authenticated": is_authenticated(),
            "csrf_token": get_csrf_token() if is_authenticated() else "",
        }

    @app.get("/login")
    def login():
        return render_template(
            "login.html",
            error=False,
            next_url=request.args.get("next", "/"),
        )

    @app.post("/login")
    def login_post():
        next_url = request.form.get("next") or "/"
        if verify_password(request.form.get("password", "")):
            login_user()
            return redirect(next_url)
        return render_template("login.html", error=True, next_url=next_url), 401

    @app.post("/logout")
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.get("/")
    def dashboard():
        connections = list_connections()
        status_items = [
            {"label": "Server", "value": "Works", "state": "ok"},
            {"label": "AmneziaWG", "value": connections[0].status, "state": "idle"},
            {"label": "Xray", "value": connections[1].status, "state": "idle"},
            {"label": "Clients", "value": str(count_clients()), "state": "idle"},
            {"label": "Traffic today", "value": "0 GB", "state": "idle"},
            {"label": "Backups", "value": str(len(list_backups())), "state": "idle"},
        ]
        return render_template("dashboard.html", active_page="dashboard", status_items=status_items)

    @app.get("/recovery")
    def recovery():
        return render_template(
            "recovery.html",
            health=health_summary(),
            health_checks=collect_health_checks(),
            backups=list_backups()[:5],
        )

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

    def _build_export(client_id: int, kind: str):
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

        return builder(client)

    @app.get("/clients/<int:client_id>/exports/<kind>")
    def export_client_access(client_id: int, kind: str):
        export = _build_export(client_id, kind)
        return Response(
            export.body,
            mimetype=export.media_type,
            headers={"Content-Disposition": f"attachment; filename={export.filename}"},
        )

    @app.get("/clients/<int:client_id>/qr/<kind>")
    def client_access_qr(client_id: int, kind: str):
        export = _build_export(client_id, kind)
        return Response(build_qr_svg(export.body), mimetype="image/svg+xml")

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
            health_checks=collect_health_checks(),
            backups=list_backups(),
            operations=list_operations(),
            release=get_release_manifest(),
        )

    @app.post("/maintenance/backups")
    def create_backup_route():
        create_backup()
        return redirect(url_for("maintenance"))

    @app.post("/maintenance/backups/<name>/restore")
    def restore_backup_route(name: str):
        if not restore_backup(name):
            abort(404)
        return redirect(url_for("maintenance"))

    @app.get("/maintenance/backups/<name>/download")
    def download_backup_route(name: str):
        backup = get_backup(name)
        if backup is None:
            abort(404)
        return send_file(backup.path, as_attachment=True, download_name=backup.name)

    @app.get("/maintenance/diagnostics.json")
    def download_diagnostics():
        return Response(
            build_diagnostic_report_json(),
            mimetype="application/json; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=sg-gateway-diagnostics.json"},
        )

    @app.get("/help")
    def help_index():
        return render_template("help.html", active_page="help", topics=list_topics(), topic=None)

    @app.get("/help/<slug>")
    def help_topic(slug: str):
        topic = get_topic(slug)
        if topic is None:
            abort(404)
        return render_template("help.html", active_page="help", topics=list_topics(), topic=topic)

    @app.get("/api/status")
    def api_status():
        report = build_diagnostic_report()
        return jsonify(
            {
                "service": report["service"],
                "version": report["version"],
                "status": report["health"],
                "environment": report["environment"],
                "clients": report["summary"]["clients"],
                "backups": report["summary"]["backups"],
                "connections": report["connections"],
                "health_checks": report["health_checks"],
            }
        )

    @app.get("/api/version")
    def api_version():
        return jsonify(get_release_manifest())

    @app.get("/health")
    def health():
        report = build_diagnostic_report()
        status_code = 200 if report["health"] in {"ok", "warning"} else 503
        return jsonify(
            {
                "service": "sg-gateway-panel",
                "version": get_version(),
                "status": report["health"],
            }
        ), status_code

    return app


app = create_app()