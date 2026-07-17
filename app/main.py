from flask import Flask, jsonify, render_template


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="web/templates",
        static_folder="web/static",
    )

    @app.get("/")
    def dashboard():
        status_items = [
            {"label": "Server", "value": "Works", "state": "ok"},
            {"label": "AmneziaWG", "value": "Not configured", "state": "idle"},
            {"label": "Xray", "value": "Not configured", "state": "idle"},
            {"label": "Clients", "value": "0", "state": "idle"},
            {"label": "Traffic today", "value": "0 GB", "state": "idle"},
            {"label": "Backup", "value": "Not created", "state": "idle"},
        ]
        return render_template("dashboard.html", status_items=status_items)

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
