from pathlib import Path
import hashlib
import subprocess

ROOT = Path('.')
BASE = '5a7cc066e402026aeb33b144675045a7011c7e27'

restore = [
    'README.md',
    'app/web/static/sg-preview28-final.css',
    'app/web/static/sg-xray-profiles-v2.css',
    'app/web/templates/connections.html',
    'app/xray/profiles.py',
    'app/xray/sg_panel_vless.py',
    'docs/CONNECTIONS.md',
    'docs/README.md',
    'docs/TECHNICAL.md',
    'tests/test_sg_gateway_021_full_publication_ru.py',
    'tests/test_sg_gateway_021_xmux_rf.py',
    'tests/test_xray_profile_flow_v23.py',
]
subprocess.run(['git', 'checkout', BASE, '--', *restore], check=True)

remove = [
    'app/xray/xmux.py',
    'tests/test_sg_gateway_02114_xmux_simple_expert_ui.py',
    'tests/test_sg_gateway_02115_connections_polish.py',
]
for rel in remove:
    path = ROOT / rel
    if path.exists():
        path.unlink()

for helper in [
    ROOT / '.github/agent-restore-pre-vless-only.py',
    ROOT / '.github/workflows/agent-restore-pre-vless-only.yml',
]:
    if helper.exists():
        helper.unlink()

# Rebuild source integrity from the final tree.
tracked = subprocess.check_output(['git', 'ls-files'], text=True).splitlines()
rows = []
for rel in tracked:
    if rel == 'SOURCE-SHA256SUMS':
        continue
    path = ROOT / rel
    if not path.is_file():
        continue
    rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel}")
(ROOT / 'SOURCE-SHA256SUMS').write_text('\n'.join(rows) + '\n', encoding='utf-8')
