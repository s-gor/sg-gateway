from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_system_visual_v1_uses_existing_context():
    template = (ROOT / "app/web/templates/system.html").read_text(encoding="utf-8")
    for marker in (
        "report.health",
        "resources.memory",
        "resources.disk",
        "resources.cpu",
        "health_checks",
        "connections",
        "client_total",
        "backup_total",
    ):
        assert marker in template


def test_system_visual_v1_has_compact_user_layout():
    template = (ROOT / "app/web/templates/system.html").read_text(encoding="utf-8")
    for marker in (
        "sv1-summary",
        "sg-ljd-system-summary",
        "sv1-resource-grid",
        "sv1-health-panel",
        "sv1-action-grid",
        "Частые операции",
    ):
        assert marker in template
    for removed in (
        "sv1-connections-panel",
        "Панель и hostd",
        "Управление системой",
    ):
        assert removed not in template


def test_system_visual_v1_quick_actions_are_real_actions():
    template = (ROOT / "app/web/templates/system.html").read_text(encoding="utf-8")
    for marker in (
        "Создать клиента",
        "Настроить подключение",
        "Создать резервную копию",
        "Скачать диагностику",
        "url_for('create_backup_route')",
        "url_for('download_diagnostics')",
        "url_for('clients', new='1')",
    ):
        assert marker in template
    quick_actions = template.split('<div class="sv1-action-grid', 1)[1].split('</div>\n    </article>', 1)[0]
    for duplicated_menu_label in (
        ">Clients<",
        ">Connections<",
        ">Maintenance<",
        ">Recovery<",
    ):
        assert duplicated_menu_label not in quick_actions


def test_system_visual_v1_uses_existing_routes():
    template = (ROOT / "app/web/templates/system.html").read_text(encoding="utf-8")
    for route in (
        "download_diagnostics",
        "maintenance",
        "api_status",
        "connections",
        "clients",
        "create_backup_route",
    ):
        assert f"url_for('{route}'" in template


def test_system_visual_v1_does_not_invent_live_traffic():
    template = (ROOT / "app/web/templates/system.html").read_text(encoding="utf-8")
    for forbidden in (
        "11.51 GB",
        "Last seen",
        "Текущая скорость",
        "SG-Node",
        "Controller",
    ):
        assert forbidden not in template


def test_system_visual_v1_css_exists():
    path = ROOT / "app/web/static/sg-system-visual-v1.css"
    assert path.is_file()
    css = path.read_text(encoding="utf-8")
    assert ".sv1-resource-grid" in css
    assert ".sv1-donut" in css
    assert ".sv1-check-list" in css
    assert ".sv1-action-button" in css
