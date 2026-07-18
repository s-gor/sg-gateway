import os
import re
import shutil
from pathlib import Path
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
    ("nl", "Netherlands"),
    ("de", "Germany"),
    ("fi", "Finland"),
    ("fr", "France"),
    ("gb", "United Kingdom"),
    ("pl", "Poland"),
    ("us", "United States"),
    ("ca", "Canada"),
    ("sg", "Singapore"),
    ("tr", "Turkey"),
    ("il", "Israel"),
    ("unknown", "Country not selected"),
]
COUNTRY_NAMES = dict(COUNTRY_OPTIONS)


def normalize_country_code(value: str | None) -> str:
    code = (value or "unknown").strip().lower()
    if not re.fullmatch(r"[a-z]{2}|unknown", code):
        return "unknown"
    return code if code in COUNTRY_NAMES else "unknown"


def country_name(code: str | None) -> str:
    return COUNTRY_NAMES.get(normalize_country_code(code), COUNTRY_NAMES["unknown"])


def _format_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    size = float(max(0, int(value or 0)))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{int(value)} B"


def _read_meminfo() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.split()[0]) * 1024
    except OSError:
        return values
    return values


def _process_rss(names: tuple[str, ...]) -> int:
    total = 0
    proc = Path("/proc")
    if not proc.exists():
        return total
    for item in proc.iterdir():
        if not item.name.isdigit():
            continue
        try:
            comm = (item / "comm").read_text(encoding="utf-8").strip().lower()
            if not any(name in comm for name in names):
                continue
            status = (item / "status").read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"VmRSS:\s+(\d+)\s+kB", status)
        if match:
            total += int(match.group(1)) * 1024
    return total


def _resource_state(percent: int) -> tuple[str, str]:
    if percent >= 95:
        return "critical", "Critical"
    if percent >= 85:
        return "high", "Low capacity"
    if percent >= 70:
        return "warning", "Warning"
    return "normal", "Normal"


def _dashboard_resources() -> dict:
    mem = _read_meminfo()
    total = mem.get("MemTotal", 0)
    available = mem.get("MemAvailable", 0)
    free = mem.get("MemFree", 0)
    cached = mem.get("Cached", 0) + mem.get("SReclaimable", 0)
    used = max(0, total - available)
    used_percent = round(used * 100 / total) if total else 0
    memory_state, memory_label = _resource_state(used_percent)

    panel = _process_rss(("python", "waitress"))
    web = _process_rss(("nginx",))
    other = max(0, used - panel - web)
    memory_parts = [
        ("panel", "SG-Gateway", "Panel and child processes", panel, "#4f9bff"),
        ("web", "Web server", "Nginx/proxy processes, when present", web, "#9b7bff"),
        ("system", "System services", "Remaining operating system processes", other, "#38c6c2"),
        ("cache", "File cache", "Memory the OS can reclaim", cached, "#e7c45b"),
        ("free", "Free", f"Available including cache: {_format_bytes(available)}", free, "#4ecb86"),
    ]

    start = 0.0
    gradient_parts: list[str] = []
    memory_rows: list[dict] = []
    for key, label, note, amount, color in memory_parts:
        percent = round(amount * 100 / total, 1) if total else 0
        end = min(100.0, start + percent)
        gradient_parts.append(f"{color} {start:.1f}% {end:.1f}%")
        memory_rows.append(
            {
                "key": key,
                "label": label,
                "note": note,
                "value": _format_bytes(amount),
                "percent": f"{percent:.1f}%",
                "color": color,
            }
        )
        start = end

    data_dir = load_config().data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    disk = shutil.disk_usage(str(data_dir))
    disk_percent = round(disk.used * 100 / disk.total) if disk.total else 0
    disk_state, disk_label = _resource_state(disk_percent)

    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    cpu_count = os.cpu_count() or 1

    return {
        "memory": {
            "used": _format_bytes(used),
            "total": _format_bytes(total),
            "available": _format_bytes(available),
            "percent": used_percent,
            "percent_text": f"{used_percent}%",
            "state": memory_state,
            "state_label": memory_label,
            "gradient": "conic-gradient(" + ", ".join(gradient_parts) + ")",
            "rows": memory_rows,
            "swap_used": _format_bytes(mem.get("SwapTotal", 0) - mem.get("SwapFree", 0)),
        },
        "disk": {
            "used": _format_bytes(disk.used),
            "free": _format_bytes(disk.free),
            "total": _format_bytes(disk.total),
            "percent": disk_percent,
            "percent_text": f"{disk_percent}%",
            "free_percent": max(0, 100 - disk_percent),
            "state": disk_state,
            "state_label": disk_label,
            "gradient": (
                "conic-gradient(#4f9bff 0 "
                f"{disk_percent}%, #4ecb86 {disk_percent}% 100%)"
            ),
        },
        "cpu": {
            "count": cpu_count,
            "load": f"{load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}",
            "percent": min(100, round((load[0] / cpu_count) * 100)) if cpu_count else 0,
        },
    }


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
        ready_connections = sum(1 for connection in connections if connection.status == "Configured")
        connection_total = len(connections) or 1
        ready_percent = round(ready_connections * 100 / connection_total)
        activity_percent = min(100, max(8, client_total * 14))
        dashboard_dials = [
            {
                "title": "Connection readiness",
                "label": "ready",
                "value": f"{ready_percent}%",
                "percent": ready_percent,
                "status": "normal" if ready_percent == 100 else "warning",
                "detail": f"{ready_connections} of {connection_total} connection engines are configured.",
            },
            {
                "title": "Clients",
                "label": "clients",
                "value": str(client_total),
                "percent": activity_percent,
                "status": "normal" if client_total else "warning",
                "detail": "Traffic today: 0 GB. Live traffic counters will appear with engine telemetry.",
            },
        ]
        status_items = [
            {"label": "Server", "value": "Running", "state": "ok"},
            {"label": "AmneziaWG", "value": connections[0].status, "state": "idle"},
            {"label": "Xray", "value": connections[1].status, "state": "idle"},
            {"label": "Clients", "value": str(client_total), "state": "idle"},
            {"label": "Traffic today", "value": "0 GB", "state": "idle"},
            {"label": "Backups", "value": str(backup_total), "state": "idle"},
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

    @app.get("/system")
    def system():
        report = build_diagnostic_report()
        return render_template(
            "system.html",
            active_page="system",
            report=report,
            health_checks=collect_health_checks(),
            resources=_dashboard_resources(),
        )

    @app.get("/routing")
    def routing():
        return render_template(
            "routing.html",
            active_page="routing",
            connections=list_connections(),
            awg_settings=get_connection_settings("amneziawg"),
            xray_settings=get_connection_settings("xray"),
        )

    @app.get("/security")
    def security():
        network_accessible = config.host not in {"127.0.0.1", "localhost", "::1"}
        default_password = config.admin_password == "admin"
        return render_template(
            "security.html",
            active_page="security",
            security={
                "host": config.host,
                "port": config.port,
                "environment": config.environment,
                "network_accessible": network_accessible,
                "default_password": default_password,
                "exposure": (
                    "The panel is bound to a network-accessible interface."
                    if network_accessible
                    else "The panel is bound to a local interface."
                ),
                "password_message": (
                    "The default development password is still active."
                    if default_password
                    else "A custom administrator password is configured."
                ),
            },
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
            flash("Client created.", "success")
            return redirect(url_for("client_detail", client_id=client_id))
        flash("Client was not created. Check the name: it must be unique and 80 characters or fewer.", "error")
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
        flash("AmneziaWG settings saved." if updated else "AmneziaWG settings were not applied. Check host and port.", "success" if updated else "error")
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
        flash("Xray settings saved." if updated else "Xray settings were not applied. Check host and port.", "success" if updated else "error")
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
        flash(f"Backup created: {backup.name}", "success")
        return redirect(url_for("maintenance"))

    @app.post("/maintenance/backups/<name>/restore")
    def restore_backup_route(name: str):
        if not restore_backup(name):
            flash("Backup not found.", "error")
            return redirect(url_for("maintenance"))
        flash(f"Backup restored: {name}", "success")
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
