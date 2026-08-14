from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_clean_install_keeps_warp_helper_but_never_auto_registers_warp() -> None:
    body = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "install_wgcf_from_vendor" in body
    assert "[Engine 5/5] WARP wgcf-cli" in body
    assert 'run_quiet "Этап 10/10 · Создание и активация WARP" stage9_ensure_warp' not in body
    assert 'run_hidden "Этап 9/9 · 4/6 · Создание и активация WARP" stage9_ensure_warp' not in body
    assert "WARP:         создан и активен" not in body
    assert "helper установлен; создаётся при необходимости в Outbounds" in body


def test_manual_warp_creation_remains_available_after_install() -> None:
    outbounds = (ROOT / "app/web/templates/outbounds.html").read_text(encoding="utf-8")
    commands = (ROOT / "hostd/sg_hostd/commands.py").read_text(encoding="utf-8")
    assert "Создать WARP" in outbounds
    assert "warp.install" in commands
