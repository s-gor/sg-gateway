#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

EXPECTED = {
    "install.sh": "8ad35fcb7e1671b1582223ccbb345333f2f4afae",
    "deploy/install-from-github.sh": "b7f77c067d2b0db85eb820fa58d9a17192070329",
    "app/install_seed.py": "779ad6dd93da105f68658b119aa8da1ea23c713a",
    "app/mihomo/service.py": "840cdd2bca53fef2aafd9aee5ccb161228a5ae11",
    "app/web/templates/clients.html": "0df9105577452a5f982471395e18b81f4ed5235d",
    "tests/test_sg_gateway_020_retest_installer.py": "bd8e27e8c9b0bfaaf4bffb0a6d511aec0b0efd0e",
    "tests/test_preview51_installer_contract.py": "d55d00ba4f6a39c4ad9abcfe24f8184177d8c04a",
    "tests/test_sg_gateway_017_warp_panel_port.py": "b00de707fe3de8e60d8f24c7ee6e4f3deedcb115",
}


def blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def read(rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one marker, found {count}")
    return text.replace(old, new, 1)


for rel, expected in EXPECTED.items():
    path = root / rel
    if not path.is_file():
        raise RuntimeError(f"missing current-main file: {rel}")
    found = blob_sha(path)
    if found != expected:
        raise RuntimeError(f"{rel}: expected Git blob {expected}, found {found}")

# ---------------------------------------------------------------------------
# Full mandatory port preflight.
# ---------------------------------------------------------------------------
preflight = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import errno
import os
import socket
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PortSpec:
    label: str
    protocol: str
    port: int
    scope: str = "public"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for name in (
        "panel", "xray", "awg", "mieru", "xhttp_reality", "xhttp_tls",
        "hysteria2", "anytls", "tuic", "hostd", "backend",
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=int, required=True)
    return parser.parse_args()


def port_specs(args: argparse.Namespace) -> list[PortSpec]:
    return [
        PortSpec("Nginx HTTP / ACME", "tcp", 80),
        PortSpec("Панель SG-Gateway", "tcp", args.panel),
        PortSpec("VLESS Reality TCP", "tcp", args.xray),
        PortSpec("Mieru", "tcp", args.mieru),
        PortSpec("VLESS XHTTP Reality", "tcp", args.xhttp_reality),
        PortSpec("VLESS XHTTP TLS", "tcp", args.xhttp_tls),
        PortSpec("AnyTLS", "tcp", args.anytls),
        PortSpec("SG-HostD", "tcp", args.hostd, "loopback"),
        PortSpec("Backend панели", "tcp", args.backend, "loopback"),
        PortSpec("AmneziaWG", "udp", args.awg),
        PortSpec("Hysteria2", "udp", args.hysteria2),
        PortSpec("TUIC v5", "udp", args.tuic),
    ]


def duplicate_errors(items: list[PortSpec]) -> list[str]:
    grouped: dict[tuple[str, int], list[str]] = {}
    errors: list[str] = []
    for item in items:
        if not 1 <= item.port <= 65535:
            errors.append(f"{item.label}: недопустимый порт {item.port}")
            continue
        grouped.setdefault((item.protocol, item.port), []).append(item.label)
    for (protocol, port), labels in grouped.items():
        if len(labels) > 1:
            errors.append(
                f"{port}/{protocol.upper()} одновременно назначен: " + ", ".join(labels)
            )
    return errors


def bind_check(item: PortSpec, family: socket.AddressFamily) -> tuple[bool, str]:
    sock_type = socket.SOCK_STREAM if item.protocol == "tcp" else socket.SOCK_DGRAM
    if family == socket.AF_INET:
        host = "127.0.0.1" if item.scope == "loopback" else "0.0.0.0"
        address = (host, item.port)
    else:
        host = "::1" if item.scope == "loopback" else "::"
        address = (host, item.port, 0, 0)
    sock = socket.socket(family, sock_type)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        if family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.bind(address)
        if sock_type == socket.SOCK_STREAM:
            sock.listen(1)
        return True, ""
    except OSError as exc:
        if family == socket.AF_INET6 and exc.errno in {
            errno.EAFNOSUPPORT, errno.EADDRNOTAVAIL,
        }:
            return True, "IPv6 недоступен"
        return False, os.strerror(exc.errno) if exc.errno else str(exc)
    finally:
        sock.close()


def socket_inodes(protocol: str, port: int) -> set[str]:
    names = (
        ("/proc/net/tcp", "/proc/net/tcp6")
        if protocol == "tcp"
        else ("/proc/net/udp", "/proc/net/udp6")
    )
    wanted = f"{port:04X}"
    result: set[str] = set()
    for name in names:
        try:
            lines = Path(name).read_text(encoding="ascii", errors="ignore").splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 10:
                continue
            if fields[1].rpartition(":")[2].upper() != wanted:
                continue
            if protocol == "tcp" and fields[3] != "0A":
                continue
            result.add(fields[9])
    return result


def owners(protocol: str, port: int) -> list[str]:
    inodes = socket_inodes(protocol, port)
    if not inodes:
        return []
    found: list[str] = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            fds = list((proc / "fd").iterdir())
        except OSError:
            continue
        matched = False
        for fd in fds:
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target.startswith("socket:[") and target[8:-1] in inodes:
                matched = True
                break
        if not matched:
            continue
        try:
            command = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            ).strip()
        except OSError:
            command = ""
        try:
            name = (proc / "comm").read_text(encoding="utf-8", errors="replace").strip()
        except OSError:
            name = "unknown"
        found.append(f"PID {proc.name}; процесс={name}; команда={command or name}")
    return sorted(set(found))


def main() -> int:
    items = port_specs(arguments())
    errors = duplicate_errors(items)
    if errors:
        print("[SG-Gateway] [PORT ERROR] Конфликт портов в параметрах установки:")
        for error in errors:
            print("  - " + error)
        return 1

    print("[SG-Gateway] Проверка обязательных портов до изменения сервера:")
    conflicts: list[tuple[PortSpec, list[str]]] = []
    for item in items:
        failures: list[str] = []
        for family, label in ((socket.AF_INET, "IPv4"), (socket.AF_INET6, "IPv6")):
            ok, note = bind_check(item, family)
            if not ok:
                failures.append(f"{label}: {note}")
        if failures:
            conflicts.append((item, failures))
            print(f"  [ЗАНЯТ] {item.port}/{item.protocol.upper():3} — {item.label}")
        else:
            print(f"  [OK]    {item.port}/{item.protocol.upper():3} — {item.label}")

    if not conflicts:
        print("[SG-Gateway] [OK] Все обязательные TCP/UDP-порты свободны.")
        return 0

    print("\n[SG-Gateway] [PORT ERROR] Установка остановлена до backup и копирования файлов.")
    for item, failures in conflicts:
        print(f"\n{item.label}: {item.port}/{item.protocol.upper()}")
        for failure in failures:
            print("  " + failure)
        details = owners(item.protocol, item.port)
        for detail in details or ["Процесс не определён через /proc; проверьте ss -lntup."]:
            print("  " + detail)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''
write("deploy/installer-port-preflight.py", preflight)
(root / "deploy/installer-port-preflight.py").chmod(0o755)

# ---------------------------------------------------------------------------
# Native installer: no fresh-install questions, auto password, early/full
# preflight, no automatic VPN clients.
# ---------------------------------------------------------------------------
rel = "install.sh"
text = read(rel)
if text.count('CREATE_SG_ADMIN="1"') != 3:
    raise RuntimeError("unexpected CREATE_SG_ADMIN=1 count")
text = text.replace('CREATE_SG_ADMIN="1"', 'CREATE_SG_ADMIN="0"')
text = text.replace('${CREATE_SG_ADMIN:-1}', '${CREATE_SG_ADMIN:-0}')

password_pattern = re.compile(r'(?ms)^read_password\(\) \{.*?^\}\n\nvalid_port\(\) \{')
password_replacement = r'''generate_admin_password() {
  ADMIN_PASSWORD="$(python3 - <<'PYADMINPASSWORD'
import secrets
print(secrets.token_urlsafe(24))
PYADMINPASSWORD
)"
  [[ ${#ADMIN_PASSWORD} -ge 24 ]] || {
    echo "Не удалось создать сильный пароль панели." >&2
    return 1
  }
  ADMIN_PASSWORD_HASH="$(python3 - "$ADMIN_PASSWORD" <<'PYADMINHASH'
import base64, hashlib, os, sys
password=sys.argv[1]
salt=os.urandom(16)
rounds=310000
digest=hashlib.pbkdf2_hmac('sha256',password.encode('utf-8'),salt,rounds)
print(f"pbkdf2_sha256${rounds}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}")
PYADMINHASH
)"
}

valid_port() {'''
text, count = password_pattern.subn(password_replacement, text, count=1)
if count != 1:
    raise RuntimeError("read_password replacement failed")

valid = '''valid_port() {
  [[ "$1" =~ ^[0-9]+$ ]] && (( 10#$1 >= 1 && 10#$1 <= 65535 ))
}
'''
preflight_function = valid + r'''

installer_port_preflight() {
  python3 "$SOURCE_DIR/deploy/installer-port-preflight.py" \
    --panel "$PANEL_PORT" \
    --xray "$XRAY_PORT" \
    --awg "$AWG_PORT" \
    --mieru "$MIHOMO_PORT" \
    --xhttp-reality "$XHTTP_REALITY_PORT" \
    --xhttp-tls "$XHTTP_TLS_PORT" \
    --hysteria2 "$HYSTERIA2_PORT" \
    --anytls "$ANYTLS_PORT" \
    --tuic "$TUIC_PORT" \
    --hostd "$HOSTD_PORT" \
    --backend "$BACKEND_PORT"
}
'''
text = one(text, valid, preflight_function, "port preflight function")

collect_pattern = re.compile(r'(?ms)^collect_answers\(\) \{.*?^\}\n\ncreate_backup\(\) \{')
collect_replacement = r'''collect_automatic_parameters() {
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
  CREATE_SG_ADMIN="0"
  generate_admin_password
  SECRET_KEY="$(python3 - <<'PYSECRET'
import secrets
print(secrets.token_hex(32))
PYSECRET
)"

  printf '[SG-Gateway] Публичный IP:       %s\n' "$PUBLIC_ADDRESS"
  printf '[SG-Gateway] Страна:             %s\n' "${COUNTRY_CODE^^}"
  printf '[SG-Gateway] Hostname:           %s\n' "$SERVER_NAME"
  printf '[SG-Gateway] Панель:             TCP %s\n' "$PANEL_PORT"
  printf '[SG-Gateway] VLESS Reality TCP:  TCP %s\n' "$XRAY_PORT"
  printf '[SG-Gateway] Reality target:     %s\n' "$REALITY_TARGET"
  printf '[SG-Gateway] Reality SNI:        %s\n' "$REALITY_SNI"
  printf '[SG-Gateway] AmneziaWG:          UDP %s\n' "$AWG_PORT"
  printf '[SG-Gateway] VPN-клиенты автоматически не создаются.\n'
  printf '[SG-Gateway] Пароль панели создан автоматически и будет показан в финале.\n\n'
}

create_backup() {'''
text, count = collect_pattern.subn(collect_replacement, text, count=1)
if count != 1:
    raise RuntimeError("collect_answers replacement failed")

old_main = '''  run_stage 1 "Подготовка Ubuntu" bootstrap_packages
  # Fail before any server mutation if our own pinned installation media is
  # missing or damaged. This is the key reproducibility guarantee of 021.
  verify_vendor_core_set
  if detect_existing_install; then
    printf '[SG-Gateway] Обнаружена установленная полная панель %s. Выполняется безопасное обновление.\\n\\n' \\
      "${EXISTING_VERSION:-неизвестной версии}"
    if (( SERVER_NAME_MIGRATION_REQUIRED == 1 )); then
      read_tty "Имя сервера и hostname SSH" SERVER_NAME "$SERVER_NAME"
      SERVER_NAME="$(normalize_hostname "$SERVER_NAME")"
      valid_hostname "$SERVER_NAME" || { echo "Недопустимое имя сервера." >&2; return 1; }
    fi
    printf '[SG-Gateway] Все параметры приняты. Дальнейшее обновление не потребует ввода.\\n\\n'
  elif detect_minimal_013_install; then
    printf '[SG-Gateway] Обнаружена рабочая база SG-Gateway 013.\\n'
    printf '[SG-Gateway] Восстанавливаю полный активный UI и сохраняю подтверждённые Xray Reality/ML-KEM ключи.\\n'
    printf '[SG-Gateway] Панель будет доступна на TCP %s. Логин и пароль SG-Gateway 013 сохраняются.\\n\\n' "$PANEL_PORT"
    printf '[SG-Gateway] Все параметры приняты. Дополнительных вопросов не будет.\\n\\n'
  else
    if ! load_resume_state; then
      collect_answers
      save_resume_state
    fi
    printf '\\n[SG-Gateway] Основная установка начинается. Дополнительных вопросов не будет.\\n\\n'
  fi

  # AmneziaWG has one canonical SG-Gateway transport port.
  AWG_PORT="$DEFAULT_AWG_PORT"
'''
new_main = '''  local fresh_install=0
  if [[ ! -f "$PREFIX/VERSION" ]]; then
    fresh_install=1
    rm -f "$RESUME_FILE"
    collect_automatic_parameters
    save_resume_state
    installer_port_preflight
    printf '[SG-Gateway] Ранняя проверка портов завершена. Ввода не требуется.\\n\\n'
  fi

  run_stage 1 "Подготовка Ubuntu" bootstrap_packages
  verify_vendor_core_set
  if detect_existing_install; then
    CREATE_SG_ADMIN="0"
    printf '[SG-Gateway] Обнаружена установленная полная панель %s. Выполняется безопасное обновление.\\n\\n' \\
      "${EXISTING_VERSION:-неизвестной версии}"
    if (( SERVER_NAME_MIGRATION_REQUIRED == 1 )); then
      printf '[SG-Gateway] Hostname автоматически нормализован: %s\\n' "$SERVER_NAME"
    fi
    printf '[SG-Gateway] Параметры, пароль и клиенты сохраняются. Вопросов не будет.\\n\\n'
  elif detect_minimal_013_install; then
    CREATE_SG_ADMIN="0"
    printf '[SG-Gateway] Обнаружена рабочая база SG-Gateway 013.\\n'
    printf '[SG-Gateway] Восстанавливаю полный UI и сохраняю подтверждённые ключи.\\n'
    printf '[SG-Gateway] Логин и пароль SG-Gateway 013 сохраняются. Вопросов не будет.\\n\\n'
  elif (( fresh_install == 0 )); then
    collect_automatic_parameters
    save_resume_state
  fi

  AWG_PORT="$DEFAULT_AWG_PORT"
  CREATE_SG_ADMIN="0"
  if (( UPDATE_MODE == 0 )); then
    installer_port_preflight
  fi
'''
text = one(text, old_main, new_main, "main noninteractive flow")

old_status = '''print_sg_admin_status() {
  [[ "$CREATE_SG_ADMIN" == "1" ]] || return 0
  printf '[SG-Gateway] Первый клиент sg-admin: создан\\n'
  printf '[SG-Gateway] Профили: Clients → sg-admin\\n'
}
'''
new_status = '''print_initial_client_status() {
  printf '[SG-Gateway] VPN-клиенты:  не создавались автоматически\\n'
  printf '[SG-Gateway] Первый клиент создаётся владельцем в разделе Clients.\\n'
}
'''
text = one(text, old_status, new_status, "client final status")
text = one(
    text,
    "  printf '[SG-Gateway] Логин:        admin\\n'\n",
    "  printf '[SG-Gateway] Логин:        admin\\n'\n"
    "  if (( UPDATE_MODE == 0 )); then\n"
    "    printf '[SG-Gateway] Пароль:       %s\\n' \"$ADMIN_PASSWORD\"\n"
    "    printf '[SG-Gateway] Сохраните пароль: повторно установщик его не показывает.\\n'\n"
    "  fi\n",
    "final generated password",
)
text = one(text, "  print_sg_admin_status\n", "  print_initial_client_status\n", "final client status call")

for forbidden in (
    "collect_answers",
    'read_tty "Имя сервера',
    'read_tty "Публичный HTTP-порт',
    'read_tty "Reality target',
    'read_tty "Reality SNI',
    'read_tty "Порт VLESS',
    'read_yes_no "Создать первого клиента sg-admin',
    "read_password",
):
    if forbidden in text:
        raise RuntimeError(f"interactive marker remains: {forbidden}")
if 'CREATE_SG_ADMIN="1"' in text:
    raise RuntimeError("automatic VPN client flag remains")
write(rel, text)

# ---------------------------------------------------------------------------
# Bootstrap checks fixed automatic ports before installing bootstrap packages.
# ---------------------------------------------------------------------------
rel = "deploy/install-from-github.sh"
text = read(rel)
text = one(
    text,
    'command -v gzip >/dev/null 2>&1 || missing_packages+=(gzip)\n',
    'command -v gzip >/dev/null 2>&1 || missing_packages+=(gzip)\n'
    'command -v python3 >/dev/null 2>&1 || missing_packages+=(python3)\n',
    "bootstrap python dependency",
)
anchor = '''[[ "$(id -u)" -eq 0 ]] || fail "run this installer through sudo"

missing_packages=()
'''
bootstrap = r'''[[ "$(id -u)" -eq 0 ]] || fail "run this installer through sudo"

bootstrap_port_preflight() {
  [[ ! -f /opt/sg-gateway/VERSION ]] || return 0
  local specs=(tcp:80 tcp:63443 tcp:443 tcp:2099 tcp:8444 tcp:8445 tcp:9443 tcp:8090 tcp:18080 udp:585 udp:8446 udp:10443)
  local item protocol port hex file local_address state found failures=0
  printf '[SG-Gateway] Early clean-server port check before bootstrap changes:\n'
  for item in "${specs[@]}"; do
    IFS=: read -r protocol port <<< "$item"
    printf -v hex '%04X' "$port"
    found=0
    if [[ "$protocol" == "tcp" ]]; then
      files=(/proc/net/tcp /proc/net/tcp6)
    else
      files=(/proc/net/udp /proc/net/udp6)
    fi
    for file in "${files[@]}"; do
      [[ -r "$file" ]] || continue
      while read -r _ local_address _ state _; do
        [[ "${local_address##*:}" == "$hex" ]] || continue
        [[ "$protocol" != "tcp" || "$state" == "0A" ]] || continue
        found=1
        break
      done < <(tail -n +2 "$file")
      (( found == 0 )) || break
    done
    if (( found == 1 )); then
      printf '  [BUSY] %s/%s\n' "$port" "${protocol^^}"
      failures=$((failures + 1))
    else
      printf '  [OK]   %s/%s\n' "$port" "${protocol^^}"
    fi
  done
  (( failures == 0 )) || fail "required port is occupied; server was not changed"
}

bootstrap_port_preflight

missing_packages=()
'''
text = one(text, anchor, bootstrap, "bootstrap early preflight")
write(rel, text)

# ---------------------------------------------------------------------------
# No automatic client and Mieru only with real assignments.
# ---------------------------------------------------------------------------
rel = "app/install_seed.py"
text = read(rel)
text = one(text, "from app.clients.repository import count_clients, create_client\n", "", "seed imports")
text = one(text, '                "mieru_enabled": True,', '                "mieru_enabled": False,', "Mieru idle")
start = text.index("    created_admin = False\n")
end = text.index('\n    mode = "migration" if update_mode else "seed"', start)
text = text[:start] + text[end + 1:]
text = one(
    text,
    '        f"xray_credentials_synchronized={synchronized_credentials}; "\n'
    '        f"sg_admin_created={int(created_admin)}"',
    '        f"xray_credentials_synchronized={synchronized_credentials}; "\n'
    '        "clients_seeded=0"',
    "seed status",
)
if "create_client(" in text or "count_clients()" in text or '"sg-admin"' in text:
    raise RuntimeError("automatic VPN client remains in install_seed.py")
write(rel, text)

rel = "app/mihomo/service.py"
text = read(rel)
text = one(
    text,
    '        "mieru_enabled": _bool(config.get("mieru_enabled", True)),',
    '        "mieru_enabled": _bool(config.get("mieru_enabled", False)),',
    "Mieru fallback",
)
anchor = '''    return result


_PLACEHOLDER_HOSTS = {
'''
helper = '''    return result


def _protocol_assignment_counts() -> dict[str, int]:
    init_db()
    mapping = {"mihomo": "mieru", "anytls": "anytls", "tuic": "tuic"}
    counts = {protocol: 0 for protocol in PROTOCOLS}
    sql = (
        "SELECT dc.engine, COUNT(*) AS amount "
        "FROM device_credentials dc "
        "JOIN devices d ON d.id = dc.device_id "
        "JOIN clients c ON c.id = d.client_id "
        "WHERE c.enabled = 1 AND d.enabled = 1 "
        "AND dc.engine IN ('mihomo', 'anytls', 'tuic') "
        "AND dc.status != 'disabled' "
        "GROUP BY dc.engine"
    )
    with connect() as connection:
        rows = connection.execute(sql).fetchall()
    for row in rows:
        protocol = mapping.get(str(row["engine"]))
        if protocol:
            counts[protocol] = int(row["amount"] or 0)
    return counts


_PLACEHOLDER_HOSTS = {
'''
text = one(text, anchor, helper, "profile assignment helper")
text = one(
    text,
    '''def build_candidate() -> dict[str, Any]:
    _ensure_dirs()
    requested_settings = _settings_payload()
    deployments = list_protocol_deployments()
    # Validate the complete Connections form first. AnyTLS/TUIC are served by
    # sing-box, but missing credentials/TLS/port conflicts must still block the
    # Apply button instead of silently leaving the form in "Не применено".
    _validate_settings(requested_settings, deployments)
    settings = dict(requested_settings)
''',
    '''def build_candidate() -> dict[str, Any]:
    _ensure_dirs()
    requested_settings = _settings_payload()
    deployments = list_protocol_deployments()
    assignment_counts = _protocol_assignment_counts()
    for protocol in PROTOCOLS:
        requested_settings[f"{protocol}_enabled"] = assignment_counts[protocol] > 0
    _validate_settings(requested_settings, deployments)
    settings = dict(requested_settings)
''',
    "automatic listener activation",
)
text = one(
    text,
    '''def overview() -> dict[str, Any]:
    _ensure_dirs()
    settings = _settings_payload()
    deployments = list_protocol_deployments()
    candidate = None
''',
    '''def overview() -> dict[str, Any]:
    _ensure_dirs()
    settings = _settings_payload()
    deployments = list_protocol_deployments()
    assignment_counts = _protocol_assignment_counts()
    for protocol in PROTOCOLS:
        settings[f"{protocol}_enabled"] = assignment_counts[protocol] > 0
    candidate = None
''',
    "overview listener state",
)
write(rel, text)

# ---------------------------------------------------------------------------
# Clients empty state and sensible first-client defaults.
# ---------------------------------------------------------------------------
rel = "app/web/templates/clients.html"
text = read(rel)
text = one(text, "        Добавить клиента\n", "        {{ 'Создать первого клиента' if not clients else 'Добавить клиента' }}\n", "main client button")
text = one(
    text,
    '''  {% if clients %}
  <section class="cv2-list-panel cv15-list-panel" aria-label="Список клиентов">
''',
    '''  {% if not clients %}
  <section class="cv2-list-panel cv15-list-panel sg-ljd-card" aria-label="Первый клиент">
    <div class="cv15-no-results" style="display:flex" data-sg-empty-clients="1">
      <strong>Клиентов пока нет</strong>
      <span>SG-Gateway установлен и готов. Создайте первого клиента и выберите нужные профили.</span>
      <button class="button primary sg-ljd-key-action" type="button" data-open-client-form>Создать первого клиента</button>
    </div>
  </section>
  {% else %}
  <section class="cv2-list-panel cv15-list-panel" aria-label="Список клиентов">
''',
    "empty clients state",
)
text = one(
    text,
    '<header class="cv2-dialog-head"><div><div class="cv2-kicker"><span></span> НОВЫЙ КЛИЕНТ</div><h2>Добавить клиента</h2><p>Основное устройство создаётся автоматически. Технические ключи панель подготовит сама.</p></div>',
    '<header class="cv2-dialog-head"><div><div class="cv2-kicker"><span></span> НОВЫЙ КЛИЕНТ</div><h2>{{ \'Создать первого клиента\' if not clients else \'Добавить клиента\' }}</h2><p>Выберите нужные профили. Панель подготовит реквизиты и применит конфигурацию.</p></div>',
    "dialog title",
)
text = one(
    text,
    "{% if profile.ready and profile.id == 'xhttp_reality' %}checked{% elif not profile.ready %}disabled{% endif %}",
    "{% if profile.ready and profile.id in ['reality_tcp', 'xhttp_reality'] %}checked{% elif not profile.ready %}disabled{% endif %}",
    "Xray defaults",
)
text = one(
    text,
    '<label class="cv10-protocol"><input type="checkbox" name="protocols" value="amneziawg"><span><strong>AmneziaWG</strong>',
    '<label class="cv10-protocol"><input type="checkbox" name="protocols" value="amneziawg" checked><span><strong>AmneziaWG</strong>',
    "AWG default",
)
write(rel, text)

# ---------------------------------------------------------------------------
# Update stale test and manifest assertions.
# ---------------------------------------------------------------------------
rel = "tests/test_sg_gateway_020_retest_installer.py"
text = read(rel)
text = one(text, '    assert update["sg_admin_enter_defaults_to_yes"] is True\n', '    assert update["noninteractive_install"] is True\n', "manifest test")
old_test = '''def test_sg_admin_prompt_has_explicit_enter_yes_default() -> None:
    assert 'local suffix="[Enter = Да / n = Нет]"' in INSTALL
    assert 'read_yes_no "Создать первого клиента sg-admin и сразу подготовить ссылки?" CREATE_SG_ADMIN 1' in INSTALL
    assert 'answer="${answer:-$([[ "$default_value" == "1" ]] && echo y || echo n)}"' in INSTALL
'''
new_test = '''def test_fresh_install_is_noninteractive_and_creates_no_vpn_client() -> None:
    assert "collect_automatic_parameters" in INSTALL
    assert "collect_answers" not in INSTALL
    assert "Создать первого клиента sg-admin" not in INSTALL
    assert 'CREATE_SG_ADMIN="1"' not in INSTALL
    assert "installer_port_preflight" in INSTALL
    assert "generate_admin_password" in INSTALL
'''
text = one(text, old_test, new_test, "obsolete sg-admin test")
text = one(text, '    assert "print_sg_admin_status" in final\n    assert "Профили: Clients → sg-admin" in INSTALL\n', '    assert "print_initial_client_status" in final\n    assert "Пароль:       %s" in final\n', "final output test")
write(rel, text)

rel = "tests/test_preview51_installer_contract.py"
text = read(rel)
old = '''def test_same_ec2_retry_identity_ip_country_and_admin_prompts():
    for token in (
        "detect_public_ip()",
        "checkip.amazonaws.com",
        "latest/meta-data/public-ipv4",
        "detect_country_code()",
        "Имя сервера и hostname SSH",
        "hostnamectl set-hostname",
        "Создать первого клиента sg-admin",
        "SG_GATEWAY_CREATE_SG_ADMIN",
        "SG_GATEWAY_SERVER_NAME",
        "SG_GATEWAY_COUNTRY_CODE",
        "Повторный запуск выполняется на этом же EC2",
    ):
        assert token in INSTALLER
'''
new = '''def test_same_ec2_retry_identity_ip_country_and_noninteractive_contract():
    for token in (
        "detect_public_ip()",
        "checkip.amazonaws.com",
        "latest/meta-data/public-ipv4",
        "detect_country_code()",
        "collect_automatic_parameters",
        "installer_port_preflight",
        "generate_admin_password",
        "hostnamectl set-hostname",
        "SG_GATEWAY_CREATE_SG_ADMIN",
        "SG_GATEWAY_SERVER_NAME",
        "SG_GATEWAY_COUNTRY_CODE",
        "Повторный запуск выполняется на этом же EC2",
    ):
        assert token in INSTALLER
    assert "Создать первого клиента sg-admin" not in INSTALLER
    assert 'CREATE_SG_ADMIN="1"' not in INSTALLER
'''
text = one(text, old, new, "preview51 noninteractive contract")
write(rel, text)

rel = "tests/test_sg_gateway_017_warp_panel_port.py"
text = read(rel)
text = one(
    text,
    '    assert "Первый клиент sg-admin: создан" in source\n    assert "Профили: Clients → sg-admin" in source\n',
    '    assert "VPN-клиенты:  не создавались автоматически" in source\n    assert "Первый клиент создаётся владельцем в разделе Clients" in source\n',
    "warp test no automatic client",
)
write(rel, text)

rel = "release-manifest.json"
manifest = json.loads(read(rel))
manifest["client_creation"]["first_client"] = "created-by-owner"
manifest["client_creation"]["automatic_on_install"] = False
manifest["installer_update"].pop("sg_admin_enter_defaults_to_yes", None)
manifest["installer_update"]["noninteractive_install"] = True
manifest["installer_update"]["mandatory_port_preflight"] = "before-bootstrap-and-before-mutation"
manifest["installer_requirements"]["server_name_prompt"] = False
manifest["installer_requirements"]["optional_sg_admin"] = False
manifest["installer_requirements"]["sg_admin_default"] = "not-created"
manifest["installer_requirements"]["automatic_panel_password"] = True
manifest["installer_requirements"]["mandatory_port_preflight"] = True
write(rel, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

# Documentation.
rel = "docs/INSTALLATION.md"
text = read(rel)
text = text.replace(
    "3. определяет публичный IPv4 и страну;\n4. запрашивает основные параметры;\n5. создаёт пользователя и каталоги SG-Gateway;",
    "3. автоматически определяет публичный IPv4, страну и hostname;\n4. автоматически назначает порты и проверяет их до изменений сервера;\n5. создаёт сильный пароль панели, пользователя и каталоги SG-Gateway;",
)
block = '''## Автоматические параметры чистой установки

Установщик не задаёт вопросов. Он автоматически использует hostname `sg-gateway-<страна>`, панель `63443/TCP`, VLESS Reality `443/TCP`, AmneziaWG `585/UDP`, Reality target `www.bing.com:443` и SNI `www.bing.com`.

До установки bootstrap-пакетов и повторно до изменения SG-Gateway проверяются все обязательные TCP/UDP-порты. При конфликте установка прекращается. VPN-клиенты автоматически не создаются: владелец создаёт первого клиента в разделе `Clients`. Пароль панели генерируется автоматически и показывается один раз в финальном выводе.

'''
text = text.replace("## Что делает установщик\n", block + "## Что делает установщик\n", 1)
write(rel, text)

# Dedicated regression test.
write(
    "tests/test_installer_noninteractive_port_preflight.py",
    '''from pathlib import Path

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
''',
)

# Final invariants.
install = read("install.sh")
seed = read("app/install_seed.py")
bootstrap_source = read("deploy/install-from-github.sh")
assert "collect_answers" not in install
assert "Создать первого клиента sg-admin" not in install
assert 'CREATE_SG_ADMIN="1"' not in install
assert "read_password" not in install
assert install.index("installer_port_preflight", install.index("local fresh_install=0")) < install.index('run_stage 1 "Подготовка Ubuntu"')
assert install.rindex("installer_port_preflight", 0, install.index("MUTATION_STARTED=1")) < install.index("MUTATION_STARTED=1")
assert "create_client(" not in seed and '"sg-admin"' not in seed
assert "bootstrap_port_preflight" in bootstrap_source
print("Installer contract merged: zero questions, mandatory early port checks, zero automatic VPN clients")
