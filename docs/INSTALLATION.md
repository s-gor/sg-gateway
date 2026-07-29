# Установка и обновление SG-Gateway

## Требования

- чистая Ubuntu Server 24.04;
- root-доступ через `sudo`;
- публичный IPv4;
- открытый публичный порт панели;
- свободные порты выбранных VPN/proxy-профилей.

### Порты AWS Security Group / firewall

Стандартные порты SG-Gateway по возрастанию:

| Порт | Протокол | Назначение |
|---:|:---:|---|
| `22` | TCP | SSH; лучше разрешить только со своего IP |
| `80` | TCP | HTTP / Let’s Encrypt |
| `443` | TCP | VLESS Reality TCP |
| `585` | UDP | AmneziaWG, фиксированный порт |
| `2099` | TCP | Mieru, транспорт по умолчанию |
| `8444` | TCP | VLESS XHTTP Reality |
| `8445` | TCP | VLESS XHTTP TLS |
| `8446` | UDP | Hysteria 2 |
| `9443` | TCP | AnyTLS |
| `10443` | UDP | TUIC v5 |
| `63443` | TCP | Веб-панель SG-Gateway |

Открывайте только используемые VPN-профили. Для Mieru при выборе UDP откройте `2099/UDP` вместо `2099/TCP`. Для изменённого в панели порта откройте именно новое значение. `22/TCP` и `63443/TCP` желательно ограничить IP администратора, если это возможно.

`8090/TCP` (HostD) и `18080/TCP` (backend панели) работают только на `127.0.0.1` и **не должны быть открыты наружу**. Установщик может добавить правила UFW на сервере, но AWS Security Group необходимо настроить отдельно.

SG-Gateway устанавливается нативно и не требует Docker.

## Установка из GitHub main

```bash
sudo bash -c 'set -Eeuo pipefail; LOG=/var/log/sg-gateway-bootstrap.log; : >"$LOG"; chmod 600 "$LOG"; export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a; missing=(); for pkg in ca-certificates curl tar gzip; do dpkg-query -W -f="${db:Status-Abbrev}" "$pkg" 2>/dev/null | grep -q "^ii" || missing+=("$pkg"); done; if ((${#missing[@]})); then printf "[SG-Gateway] Installing missing Ubuntu tools...\n"; apt-get update -qq >>"$LOG" 2>&1 && apt-get install -y -qq --no-install-recommends "${missing[@]}" >>"$LOG" 2>&1 || { printf "[SG-Gateway] Bootstrap failed. Last log lines:\n" >&2; tail -n 80 "$LOG" >&2; exit 1; }; fi; printf "[SG-Gateway] [OK] Ubuntu tools ready\n"; curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-from-github.sh | bash'
```

Bootstrap загружает текущий `main` во временный каталог, проверяет обязательные файлы и запускает нативный `install.sh`.

## Что делает установщик

1. ждёт освобождения apt/dpkg;
2. устанавливает системные зависимости;
3. определяет публичный IPv4 и страну;
4. запрашивает основные параметры;
5. создаёт пользователя и каталоги SG-Gateway;
6. устанавливает веб-панель, HostD и движки;
7. создаёт systemd-службы;
8. строит и проверяет runtime-конфигурации;
9. настраивает Nginx и UFW;
10. показывает итоговый адрес панели.

Постоянный журнал очищается от паролей, приватных ключей, PEM-блоков и клиентских ссылок.

## Начальный доступ

Свежая установка открывается по HTTP и IP. Это позволяет проверить панель до настройки домена. HTTPS включается позднее из раздела `Security`.

## Обновление

Используется та же команда, что и для установки:

```bash
sudo bash -c 'set -Eeuo pipefail; LOG=/var/log/sg-gateway-bootstrap.log; : >"$LOG"; chmod 600 "$LOG"; export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a; missing=(); for pkg in ca-certificates curl tar gzip; do dpkg-query -W -f="${db:Status-Abbrev}" "$pkg" 2>/dev/null | grep -q "^ii" || missing+=("$pkg"); done; if ((${#missing[@]})); then printf "[SG-Gateway] Installing missing Ubuntu tools...\n"; apt-get update -qq >>"$LOG" 2>&1 && apt-get install -y -qq --no-install-recommends "${missing[@]}" >>"$LOG" 2>&1 || { printf "[SG-Gateway] Bootstrap failed. Last log lines:\n" >&2; tail -n 80 "$LOG" >&2; exit 1; }; fi; printf "[SG-Gateway] [OK] Ubuntu tools ready\n"; curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-from-github.sh | bash'
```

При обнаружении установленной панели включается режим обновления. Перед изменением создаётся резервная копия управляемых файлов и состояния служб.

После обновления откройте панель и проверьте `System`, `Connections`, `Routing` и `Security`.
