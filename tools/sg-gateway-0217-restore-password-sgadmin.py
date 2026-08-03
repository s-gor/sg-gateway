#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
CURRENT = '257d3e3a847c19a6e370548fd718bd6a06234d16'
OLD = 'a103af884400a4ffea41505d4fa8b07c81c1682d'


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True)


def show(commit: str, path: str) -> str:
    return run('git', 'show', f'{commit}:{path}')


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8', newline='\n')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected one exact marker, found {count}')
    return text.replace(old, new, 1)


def replace_function(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf'(?ms)^def {re.escape(name)}\([^\n]*\).*?(?=^def |\Z)')
    text, count = pattern.subn(body.rstrip() + '\n\n', text, count=1)
    if count != 1:
        raise RuntimeError(f'test function not found: {name}')
    return text


head = run('git', 'rev-parse', 'HEAD').strip()
parent = run('git', 'rev-parse', 'HEAD^').strip()
if head != CURRENT and parent != CURRENT:
    raise RuntimeError(f'expected current main or trigger parent {CURRENT}, found head={head} parent={parent}')

# ---------------------------------------------------------------------------
# install.sh: automatic technical values, one password dialog, automatic
# sg-admin, and no port preflight of any kind.
# ---------------------------------------------------------------------------
install = read('install.sh')
old_install = show(OLD, 'install.sh')

password_match = re.search(r'(?ms)^read_password\(\) \{.*?^\}\n\n', old_install)
if not password_match:
    raise RuntimeError('accepted read_password function not found')
accepted_password_function = password_match.group(0)

install, count = re.subn(
    r'(?ms)^generate_admin_password\(\) \{.*?^\}\n\n',
    accepted_password_function,
    install,
    count=1,
)
if count != 1:
    raise RuntimeError('generated-password function not found')

install, count = re.subn(
    r'(?ms)^installer_port_preflight\(\) \{.*?^\}\n\n',
    '',
    install,
    count=1,
)
if count != 1:
    raise RuntimeError('installer port-preflight function not found')

collect = r'''collect_automatic_parameters() {
  printf "\n%s[SG-Gateway]%s Автоматические параметры установки\n" "$CYAN" "$RESET"

  PUBLIC_ADDRESS="$(detect_public_ip || true)"
  valid_public_ipv4 "$PUBLIC_ADDRESS" || {
    echo "Не удалось автоматически определить корректный публичный IPv4." >&2
    return 1
  }
  COUNTRY_CODE="$(detect_country_code "$PUBLIC_ADDRESS")"
  SERVER_NAME="sg-gateway"
  [[ "$COUNTRY_CODE" != "unknown" ]] && SERVER_NAME="sg-gateway-${COUNTRY_CODE}"
  SERVER_NAME="$(normalize_hostname "$SERVER_NAME")"
  valid_hostname "$SERVER_NAME" || return 1

  PANEL_PORT="$DEFAULT_PANEL_PORT"
  XRAY_PORT="$DEFAULT_XRAY_PORT"
  AWG_PORT="$DEFAULT_AWG_PORT"
  REALITY_TARGET="$DEFAULT_REALITY_TARGET"
  REALITY_SNI="$DEFAULT_REALITY_SNI"
  CREATE_SG_ADMIN="1"

  printf '[SG-Gateway] Публичный IP:       %s\n' "$PUBLIC_ADDRESS"
  printf '[SG-Gateway] Страна:             %s\n' "${COUNTRY_CODE^^}"
  printf '[SG-Gateway] Hostname:           %s\n' "$SERVER_NAME"
  printf '[SG-Gateway] Панель:             TCP %s\n' "$PANEL_PORT"
  printf '[SG-Gateway] VLESS Reality TCP:  TCP %s\n' "$XRAY_PORT"
  printf '[SG-Gateway] Reality target:     %s\n' "$REALITY_TARGET"
  printf '[SG-Gateway] Reality SNI:        %s\n' "$REALITY_SNI"
  printf '[SG-Gateway] AmneziaWG:          UDP %s\n' "$AWG_PORT"
  printf '[SG-Gateway] Первый VPN-клиент sg-admin будет создан автоматически.\n'
  printf '[SG-Gateway] Профили sg-admin: Reality TCP, XHTTP Reality, AmneziaWG, Mieru.\n\n'

  read_password
  SECRET_KEY="$(python3 - <<'PYSECRET'
import secrets
print(secrets.token_hex(32))
PYSECRET
)"
}
'''
install, count = re.subn(
    r'(?ms)^collect_automatic_parameters\(\) \{.*?^\}\n\n(?=create_backup\(\))',
    collect + '\n',
    install,
    count=1,
)
if count != 1:
    raise RuntimeError('automatic parameter function not found')

fresh_old = '''  local fresh_install=0
  if [[ ! -f "$PREFIX/VERSION" ]]; then
    fresh_install=1
    rm -f "$RESUME_FILE"
    collect_automatic_parameters
    save_resume_state
    installer_port_preflight
    printf '[SG-Gateway] Ранняя проверка портов завершена. Ввода не требуется.\\n\\n'
  fi
'''
fresh_new = '''  local fresh_install=0
  if [[ ! -f "$PREFIX/VERSION" ]]; then
    fresh_install=1
    rm -f "$RESUME_FILE"
    collect_automatic_parameters
    save_resume_state
    printf '[SG-Gateway] Автоматические параметры приняты. Основная установка начинается.\\n\\n'
  fi
'''
install = replace_once(install, fresh_old, fresh_new, 'fresh installation flow')

pre_mutation_old = '''  AWG_PORT="$DEFAULT_AWG_PORT"
  CREATE_SG_ADMIN="0"
  if (( UPDATE_MODE == 0 )); then
    installer_port_preflight
  fi
'''
pre_mutation_new = '''  AWG_PORT="$DEFAULT_AWG_PORT"
  if (( UPDATE_MODE == 0 )); then
    CREATE_SG_ADMIN="1"
  else
    CREATE_SG_ADMIN="0"
  fi
'''
install = replace_once(install, pre_mutation_old, pre_mutation_new, 'remove pre-mutation port check')

status_old = '''print_initial_client_status() {
  printf '[SG-Gateway] VPN-клиенты:  не создавались автоматически\\n'
  printf '[SG-Gateway] Первый клиент создаётся владельцем в разделе Clients.\\n'
}
'''
status_new = '''print_sg_admin_status() {
  [[ "$CREATE_SG_ADMIN" == "1" ]] || return 0
  printf '[SG-Gateway] Первый клиент sg-admin: создан\\n'
  printf '[SG-Gateway] Профили sg-admin: Reality TCP, XHTTP Reality, AmneziaWG, Mieru\\n'
  printf '[SG-Gateway] Создайте собственных пользователей в разделе Clients.\\n'
}
'''
install = replace_once(install, status_old, status_new, 'final sg-admin status')
install = replace_once(install, '  print_initial_client_status\n', '  print_sg_admin_status\n', 'final status call')

password_output = '''  if (( UPDATE_MODE == 0 )); then
    printf '[SG-Gateway] Пароль:       %s\\n' "$ADMIN_PASSWORD"
    printf '[SG-Gateway] Сохраните пароль: повторно установщик его не показывает.\\n'
  fi
'''
install = replace_once(install, password_output, '', 'remove echoed password')

for forbidden in (
    'installer_port_preflight',
    'generate_admin_password',
    'Ранняя проверка портов',
    'Проверка обязательных портов',
):
    if forbidden in install:
        raise RuntimeError(f'forbidden port/generated-password marker remains: {forbidden}')
if install.count('  read_password\n') != 1:
    raise RuntimeError('password prompt must be called exactly once')
if 'CREATE_SG_ADMIN="1"' not in install:
    raise RuntimeError('automatic sg-admin flag missing')
write('install.sh', install)

# Bootstrap returns to the accepted scheme: download and start, no port checks.
write('deploy/install-from-github.sh', show(OLD, 'deploy/install-from-github.sh'))
(ROOT / 'deploy/installer-port-preflight.py').unlink(missing_ok=True)

# Restore the accepted client/runtime source, then give sg-admin the accepted
# four visible non-HTTPS profiles plus hidden SG Client subscription.
seed = show(OLD, 'app/install_seed.py')
seed = replace_once(
    seed,
    '''        admin_client_id = create_client(
            "sg-admin", "xray_xhttp_reality,sgclient"
        )
''',
    '''        admin_client_id = create_client(
            "sg-admin",
            "xray_reality_tcp,xray_xhttp_reality,amneziawg,mihomo,sgclient",
        )
''',
    'sg-admin accepted profiles',
)
write('app/install_seed.py', seed)
write('app/mihomo/service.py', show(OLD, 'app/mihomo/service.py'))
write('app/web/templates/clients.html', show(OLD, 'app/web/templates/clients.html'))

# Documentation: old operational scheme, with only the password interactive.
docs = show(OLD, 'docs/INSTALLATION.md')
docs = docs.replace(
    '3. определяет публичный IPv4 и страну;\n4. запрашивает основные параметры;\n5. создаёт пользователя и каталоги SG-Gateway;',
    '3. автоматически определяет публичный IPv4, страну и hostname;\n4. автоматически назначает технические параметры и запрашивает только пароль администратора;\n5. автоматически создаёт первого клиента sg-admin, пользователя и каталоги SG-Gateway;',
)
section = '''## Схема чистой установки 021.7\n\nТехнические параметры назначаются автоматически. Единственный вопрос установщика — пароль администратора панели с повторным вводом. Проверка портов временно отключена. Первый VPN-клиент `sg-admin` создаётся автоматически с профилями Reality TCP, XHTTP Reality, AmneziaWG и Mieru.\n\n'''
if '## Что делает установщик\n' in docs:
    docs = docs.replace('## Что делает установщик\n', section + '## Что делает установщик\n', 1)
else:
    docs = section + docs
write('docs/INSTALLATION.md', docs)

# Manifest returns to the old line, explicitly recording the restored contract.
manifest = json.loads(show(OLD, 'release-manifest.json'))
manifest.setdefault('client_creation', {})['first_client'] = 'sg-admin'
manifest['client_creation']['automatic_on_install'] = True
update = manifest.setdefault('installer_update', {})
update['sg_admin_enter_defaults_to_yes'] = False
update['password_only_interactive'] = True
update['automatic_sg_admin'] = True
update['port_preflight_enabled'] = False
requirements = manifest.setdefault('installer_requirements', {})
requirements['server_name_prompt'] = False
requirements['optional_sg_admin'] = False
requirements['sg_admin_default'] = 'created'
requirements['automatic_panel_password'] = False
requirements['password_prompt'] = True
requirements['mandatory_port_preflight'] = False
write('release-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')

# Restore and update the few tests changed by the rejected port-preflight line.
test = show(OLD, 'tests/test_sg_gateway_020_retest_installer.py')
test = replace_function(
    test,
    'test_release_marks_approved_scale_and_version',
    '''def test_release_marks_approved_scale_and_version() -> None:
    assert (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "0.1.0-021.7"
    manifest = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))
    update = manifest["installer_update"]
    assert update["client_list_row_typography_v020"] == "reverted-to-approved-018-scale"
    assert update["password_only_interactive"] is True
    assert update["automatic_sg_admin"] is True
    assert update["port_preflight_enabled"] is False
    assert update["permanent_log_secret_redaction"] is True''',
)
test = replace_function(
    test,
    'test_sg_admin_prompt_has_explicit_enter_yes_default',
    '''def test_only_password_is_interactive_and_sg_admin_is_automatic() -> None:
    assert "collect_automatic_parameters" in INSTALL
    assert "read_password" in INSTALL
    assert INSTALL.count("  read_password\\n") == 1
    assert 'read_yes_no "Создать первого клиента sg-admin' not in INSTALL
    assert 'CREATE_SG_ADMIN="1"' in INSTALL
    assert "installer_port_preflight" not in INSTALL
    assert "Первый VPN-клиент sg-admin будет создан автоматически" in INSTALL''',
)
test = replace_function(
    test,
    'test_final_success_block_does_not_dump_credentials',
    '''def test_final_success_block_does_not_dump_credentials() -> None:
    final = INSTALL.rsplit("INSTALL_SUCCESS=1", 1)[1]
    assert "subscription-base64" not in final
    assert "vless://" not in final
    assert "hysteria2://" not in final
    assert "mieru://" not in final
    assert "BEGIN CERTIFICATE" not in final
    assert "BEGIN PRIVATE KEY" not in final
    assert "Пароль:       %s" not in final
    assert "print_sg_admin_status" in final
    assert "Профили sg-admin: Reality TCP, XHTTP Reality, AmneziaWG, Mieru" in INSTALL''',
)
write('tests/test_sg_gateway_020_retest_installer.py', test)

test = show(OLD, 'tests/test_preview51_installer_contract.py')
test = replace_function(
    test,
    'test_same_ec2_retry_identity_ip_country_and_admin_prompts',
    '''def test_same_ec2_retry_identity_ip_country_and_password_only_prompt():
    for token in (
        "detect_public_ip()",
        "checkip.amazonaws.com",
        "latest/meta-data/public-ipv4",
        "detect_country_code()",
        "collect_automatic_parameters",
        "read_password",
        "hostnamectl set-hostname",
        "SG_GATEWAY_CREATE_SG_ADMIN",
        "SG_GATEWAY_SERVER_NAME",
        "SG_GATEWAY_COUNTRY_CODE",
        "Повторный запуск выполняется на этом же EC2",
    ):
        assert token in INSTALLER
    assert "installer_port_preflight" not in INSTALLER
    assert 'read_yes_no "Создать первого клиента sg-admin' not in INSTALLER
    assert 'CREATE_SG_ADMIN="1"' in INSTALLER''',
)
write('tests/test_preview51_installer_contract.py', test)
write('tests/test_sg_gateway_017_warp_panel_port.py', show(OLD, 'tests/test_sg_gateway_017_warp_panel_port.py'))
(ROOT / 'tests/test_installer_noninteractive_port_preflight.py').unlink(missing_ok=True)

write(
    'tests/test_installer_password_only_auto_sg_admin.py',
    '''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "install.sh").read_text(encoding="utf-8")
BOOTSTRAP = (ROOT / "deploy/install-from-github.sh").read_text(encoding="utf-8")
SEED = (ROOT / "app/install_seed.py").read_text(encoding="utf-8")


def test_restored_installer_contract() -> None:
    assert INSTALL.count("  read_password\\n") == 1
    assert "collect_automatic_parameters" in INSTALL
    assert "generate_admin_password" not in INSTALL
    assert "installer_port_preflight" not in INSTALL
    assert "bootstrap_port_preflight" not in BOOTSTRAP
    assert "installer-port-preflight.py" not in BOOTSTRAP
    assert 'CREATE_SG_ADMIN="1"' in INSTALL
    assert 'read_yes_no "Создать первого клиента sg-admin' not in INSTALL
    assert "xray_reality_tcp,xray_xhttp_reality,amneziawg,mihomo,sgclient" in SEED
    assert "create_client(" in SEED
''',
)

# Final invariants.
install = read('install.sh')
bootstrap = read('deploy/install-from-github.sh')
seed = read('app/install_seed.py')
assert install.count('  read_password\n') == 1
assert 'installer_port_preflight' not in install
assert 'bootstrap_port_preflight' not in bootstrap
assert not (ROOT / 'deploy/installer-port-preflight.py').exists()
assert 'CREATE_SG_ADMIN="1"' in install
assert 'read_yes_no "Создать первого клиента sg-admin' not in install
assert 'xray_reality_tcp,xray_xhttp_reality,amneziawg,mihomo,sgclient' in seed
print('Restored: automatic technical values, password prompt, automatic sg-admin, no port checks')
