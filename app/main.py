import re
from flask import Flask, Response, abort, flash, jsonify, redirect, render_template, request, send_file, url_for

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
from app.version import get_release_manifest, get_version


COUNTRY_OPTIONS = [
    ("nl", "Нидерланды"),
    ("de", "Германия"),
    ("fi", "Финляндия"),
    ("fr", "Франция"),
    ("gb", "Великобритания"),
    ("pl", "Польша"),
    ("us", "США"),
    ("ca", "Канада"),
    ("sg", "Сингапур"),
    ("tr", "Турция"),
    ("il", "Израиль"),
    ("unknown", "Страна не выбрана"),
]
COUNTRY_NAMES = dict(COUNTRY_OPTIONS)


def normalize_country_code(value: str | None) -> str:
    code = (value or "unknown").strip().lower()
    if not re.fullmatch(r"[a-z]{2}|unknown", code):
        return "unknown"
    return code if code in COUNTRY_NAMES else "unknown"


def country_name(code: str | None) -> str:
    return COUNTRY_NAMES.get(normalize_country_code(code), COUNTRY_NAMES["unknown"])


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
        if is_authenticated():
            return None
        return redirect(url_for("login", next=request.path))

    @app.context_processor
    def inject_globals():
        return {
            "app_version": get_version(),
            "is_authenticated": is_authenticated(),
            "country_options": COUNTRY_OPTIONS,
            "country_name": country_name,
            "country_flag_url": lambda code: url_for("static", filename=f"flags/{normalize_country_code(code)}.svg"),
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
        client_total = count_clients()
        backup_total = len(list_backups())
        ready_connections = sum(1 for connection in connections if connection.status == "Настроено")
        connection_total = len(connections) or 1
        ready_percent = round(ready_connections * 100 / connection_total)
        activity_percent = min(100, max(8, client_total * 14))
        dashboard_dials = [
            {
                "title": "Готовность подключений",
                "label": "готово",
                "value": f"{ready_percent}%",
                "percent": ready_percent,
                "status": "normal" if ready_percent == 100 else "warning",
                "detail": f"{ready_connections} из {connection_total} способов подключения настроены.",
            },
            {
                "title": "Клиенты",
                "label": "клиентов",
                "value": str(client_total),
                "percent": activity_percent,
                "status": "normal" if client_total else "warning",
                "detail": "Трафик сегодня: 0 GB. Живую статистику подключим вместе с реальными движками.",
            },
        ]
        status_items = [
            {"label": "Сервер", "value": "Работает", "state": "ok"},
            {"label": "AmneziaWG", "value": connections[0].status, "state": "idle"},
            {"label": "Xray", "value": connections[1].status, "state": "idle"},
            {"label": "Клиенты", "value": str(client_total), "state": "idle"},
            {"label": "Трафик сегодня", "value": "0 GB", "state": "idle"},
            {"label": "Резервные копии", "value": str(backup_total), "state": "idle"},
        ]
        return render_template(
            "dashboard.html",
            active_page="dashboard",
            status_items=status_items,
            dashboard_dials=dashboard_dials,
            connections=connections,
        )

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
            expires_at=request.form.get("expires_at") or None,
        )
        if client_id:
            flash("Клиент создан.", "success")
            return redirect(url_for("client_detail", client_id=client_id))
        flash("Клиент не создан. Проверьте имя: оно должно быть уникальным и не длиннее 80 символов.", "error")
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
        if not set_client_enabled(client_id, True):
            abort(404)
        return redirect(request.referrer or url_for("clients"))

    @app.post("/clients/<int:client_id>/disable")
    def disable_client(client_id: int):
        if not set_client_enabled(client_id, False):
            abort(404)
        return redirect(request.referrer or url_for("clients"))

    @app.post("/clients/<int:client_id>/delete")
    def remove_client(client_id: int):
        if not delete_client(client_id):
            abort(404)
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
        config["country_code"] = normalize_country_code(
            request.form.get("country_code", config.get("country_code", "unknown"))
        )
        updated = update_connection_settings(
            "amneziawg",
            request.form.get("host", current.host),
            request.form.get("port", str(current.port)),
            config,
        )
        flash("Настройки AmneziaWG сохранены." if updated else "Настройки AmneziaWG не применены. Проверьте хост и порт.", "success" if updated else "error")
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
        config["country_code"] = normalize_country_code(
            request.form.get("country_code", config.get("country_code", "unknown"))
        )
        updated = update_connection_settings(
            "xray",
            request.form.get("host", current.host),
            request.form.get("port", str(current.port)),
            config,
        )
        flash("Настройки Xray сохранены." if updated else "Настройки Xray не применены. Проверьте хост и порт.", "success" if updated else "error")
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
        backup = create_backup()
        flash(f"Резервная копия создана: {backup.name}", "success")
        return redirect(url_for("maintenance"))

    @app.post("/maintenance/backups/<name>/restore")
    def restore_backup_route(name: str):
        if not restore_backup(name):
            flash("Резервная копия не найдена.", "error")
            return redirect(url_for("maintenance"))
        flash(f"Резервная копия восстановлена: {name}", "success")
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