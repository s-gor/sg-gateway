from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_installer_contract() -> None:
    install = (ROOT / "install.sh").read_text(encoding="utf-8")
    bootstrap = (ROOT / "deploy/install-from-github.sh").read_text(encoding="utf-8")
    seed = (ROOT / "app/install_seed.py").read_text(encoding="utf-8")
    assert "collect_automatic_parameters" in install
    assert "collect_answers" not in install
    assert "Создать первого клиента sg-admin" not in install
    assert 'CREATE_SG_ADMIN="1"' not in install
    assert "generate_admin_password" in install
    assert "Пароль:       %s" in install
    first_check = install.index("installer_port_preflight", install.index("local fresh_install=0"))
    packages = install.index('run_stage 1 "Подготовка Ubuntu"')
    mutation = install.index("MUTATION_STARTED=1")
    assert first_check < packages < mutation
    assert install.rindex("installer_port_preflight", 0, mutation) < mutation
    assert "bootstrap_port_preflight" in bootstrap
    assert "create_client(" not in seed
    assert '"sg-admin"' not in seed
    assert '"clients_seeded=0"' in seed
