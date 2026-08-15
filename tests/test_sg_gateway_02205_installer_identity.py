from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _main_block(body: str) -> str:
    start = body.index("main() {")
    return body[start:]


def test_02205_installer_identity_is_consistent() -> None:
    body = (ROOT / "install.sh").read_text(encoding="utf-8")
    main = _main_block(body)

    assert 'VERSION="0.1.0-022.05"' in body
    assert 'INSTALLER_BUILD="02205-sgpanel-xmux-warp-updater-r1"' in body
    assert 'INSTALL_LOG="/var/log/sg-gateway-installer-02205.log"' in body
    assert 'RESUME_FILE="/root/sg-gateway-02205-installer-resume.env"' in body

    assert "printf '\\n%sSG-Gateway %s%s\\n' \"$CYAN\" \"$VERSION\" \"$RESET\"" in main
    assert 'before-sg-gateway-02205"' in main

    assert "SG-Gateway 0.1.0-022.01" not in main
    assert "before-sg-gateway-02201" not in main


def test_02205_installer_stage_identity_remains_ten_stage() -> None:
    body = (ROOT / "install.sh").read_text(encoding="utf-8")
    main = _main_block(body)
    assert "TOTAL_STAGES=10" in body
    for stage in range(1, 11):
        assert f"run_stage {stage} " in main
    assert 'run_stage 10 "Запуск и проверка" stage10_start_and_verify' in main
