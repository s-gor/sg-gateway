from pathlib import Path

ROOT = Path('.')

xmux_path = ROOT / 'tests/test_sg_gateway_021_xmux_rf.py'
xmux = xmux_path.read_text(encoding='utf-8')
old = '''    for label in ("Xray Auto", "Standard", "Для РФ — уменьшенный", "Ручной"):\n        assert label in template\n'''
new = '''    xmux_model = (ROOT / "app/xray/xmux.py").read_text(encoding="utf-8")\n    assert 'name="xhttp_xmux_mode"' in template\n    assert "xhttp_xmux_mode_options" in template\n    for label in ("Xray Auto", "Standard", "Для РФ — уменьшенный", "Ручной"):\n        assert label in xmux_model\n'''
if old not in xmux:
    raise SystemExit('stale XMUX label assertions not found')
xmux_path.write_text(xmux.replace(old, new, 1), encoding='utf-8')

flow_path = ROOT / 'tests/test_xray_profile_flow_v23.py'
flow = flow_path.read_text(encoding='utf-8')
old = '''    xray_start = template.index('id="xray-profiles"')\n    xray_end = template.index('<details class="cnv1-advanced', xray_start)\n    xray = template[xray_start:xray_end]\n'''
new = '''    xray_start = template.index('id="xray-profiles"')\n    xray_end = template.index('</form>', xray_start)\n    xray = template[xray_start:xray_end]\n'''
if old not in flow:
    raise SystemExit('stale Xray form boundary assertion not found')
flow_path.write_text(flow.replace(old, new, 1), encoding='utf-8')
