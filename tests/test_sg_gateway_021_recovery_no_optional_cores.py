from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_installer_does_not_install_optional_cores():
    installer = read("install.sh")
    stage_start = installer.index("stage_engine_runtimes() {")
    stage_end = installer.index("\n}\n", stage_start)
    stage = installer[stage_start:stage_end]

    assert "install_mihomo" not in stage
    assert "install_sing_box" not in stage
    assert "[Engine 1/3] AmneziaWG" in stage
    assert "[Engine 2/3] Xray" in stage
    assert "[Engine 3/3] WARP" in stage
    assert "Recovery baseline" in stage


def test_optional_units_and_ports_are_not_installed_or_opened():
    installer = read("install.sh")

    assert (
        'install -m 0644 "$PREFIX/deploy/mihomo.service" '
        "/etc/systemd/system/mihomo.service"
    ) not in installer
    assert (
        'install -m 0644 "$PREFIX/deploy/sg-gateway-singbox.service" '
        "/etc/systemd/system/sg-gateway-singbox.service"
    ) not in installer

    firewall_start = installer.index("stage_firewall_and_network() {")
    firewall_end = installer.index("\n}\n", firewall_start)
    firewall = installer[firewall_start:firewall_end]
    assert "MIHOMO_PORT" not in firewall
    assert "ANYTLS_PORT" not in firewall
    assert "TUIC_PORT" not in firewall


def test_new_clients_use_xray_without_optional_cores():
    repository = read("app/clients/repository.py")
    seed = read("app/install_seed.py")
    installer = read("install.sh")

    assert '"recommended": "xray_xhttp_reality,sgclient"' in repository
    assert "xray_hysteria2,sgclient" in repository
    assert '"sg-admin", "xray_xhttp_reality,sgclient"' in seed
    assert (
        "create_client('Smoke client', "
        "'xray_xhttp_reality,sgclient')"
    ) in installer


def test_stage7_subscription_contract_is_preserved():
    installer = read("install.sh")
    assert "response.status_code in (200, 409)" in installer
    assert "Application pages and device access routes: OK" in installer


def test_readme_discloses_recovery_baseline():
    readme = read("README.md")
    assert "Временная восстановительная линия 021" in readme
    assert "Mihomo и sing-box исключены из установки" in readme
