from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tests/test_sg_gateway_021_full_publication_ru.py"
body = PATH.read_text(encoding="utf-8")
old = '''    assert "Xray Auto · рекомендуется" in template\n    assert "Показать пресеты и ручные параметры" in template\n'''
new = '''    assert "Автоматически · рекомендуется" in template\n    assert "Экспертные настройки XMUX" in template\n    assert "Технические значения пресетов" in template\n'''
if old not in body:
    raise SystemExit("old XMUX publication assertions not found")
PATH.write_text(body.replace(old, new, 1), encoding="utf-8")
