from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _function_block(body: str, name: str) -> str:
    start = body.index(f"{name}() {{")
    end = body.index("\n}\n", start) + 3
    return body[start:end]


def test_clean_install_keeps_warp_helper_but_never_auto_registers_warp() -> None:
    body = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "install_wgcf_from_vendor" in body
    assert "[Engine 5/5] WARP wgcf-cli" in body
    assert "stage9_ensure_warp()" in body  # manual helper remains implemented

    stage10 = _function_block(body, "stage10_start_and_verify")
    assert "stage9_ensure_warp" not in stage10

    final9 = _function_block(body, "run_final_stage")
    assert "Создание и активация WARP" not in final9
    assert "stage9_ensure_warp" not in final9

    assert "WARP:         создан и активен" not in body
    assert "helper установлен; создаётся при необходимости в Outbounds" in body
    assert "существующий профиль сохранён" in body


def test_manual_warp_creation_remains_available_after_install() -> None:
    outbounds = (ROOT / "app/web/templates/outbounds.html").read_text(encoding="utf-8")
    commands = (ROOT / "hostd/sg_hostd/commands.py").read_text(encoding="utf-8")
    assert "Создать WARP" in outbounds
    assert "warp.install" in commands
