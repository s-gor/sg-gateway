from pathlib import Path


def test_deploy_scripts_exist():
    root = Path(__file__).resolve().parents[1]

    assert (root / "deploy" / "install.sh").exists()
    assert (root / "deploy" / "update.sh").exists()
    assert (root / "deploy" / "rollback.sh").exists()
    assert (root / "deploy" / "uninstall.sh").exists()


def test_installer_defaults_to_dry_run():
    root = Path(__file__).resolve().parents[1]
    installer = (root / "deploy" / "install.sh").read_text(encoding="utf-8")

    assert 'DRY_RUN="${SG_GATEWAY_DRY_RUN:-1}"' in installer
    assert "SG_GATEWAY_DRY_RUN=0" in installer