from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_02112_clean_install_does_not_auto_install_warp() -> None:
    text = (ROOT / 'install.sh').read_text(encoding='utf-8')
    start = text.index('run_final_stage()')
    end = text.index('verify_client_identities_after_update()', start)
    block = text[start:end]
    assert 'stage9_ensure_warp' not in block
    assert 'Создание и активация WARP' not in block
    assert '3/5 · Сохранение/применение Xray runtime' in block
    assert '4/5 · Запуск панели' in block
    assert '5/5 · Проверка Nginx и служб' in block

def test_02112_keeps_manual_warp_hostd_capability() -> None:
    text = (ROOT / 'install.sh').read_text(encoding='utf-8')
    assert '"warp.install"' in text
    assert 'stage9_ensure_warp()' in text
