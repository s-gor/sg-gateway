from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "install.sh").read_text(encoding="utf-8")
SEED = (ROOT / "app/install_seed.py").read_text(encoding="utf-8")


def test_sg_admin_is_clean_install_only_and_update_preserves_empty_clients():
    assert "not update_mode" in SEED
    assert 'CREATE_SG_ADMIN="0"' in INSTALL
    assert "existing_clients == 0" not in INSTALL


def test_first_sg_admin_gets_every_non_certificate_access_only():
    assert '"amneziawg,xray_reality_tcp,xray_xhttp_reality,mihomo,sgclient"' in SEED
    for forbidden in ("xray_xhttp_tls", "xray_hysteria2", "anytls", "tuic"):
        assert forbidden not in SEED.split('admin_client_id = create_client(', 1)[1].split(')', 1)[0]


def test_installer_explains_certificate_boundary():
    assert "обычный VPN-клиент, не системный пользователь" in INSTALL
    assert "Без сертификата ему сразу доступны" in INSTALL
    assert "После настройки HTTPS можно добавить" in INSTALL
