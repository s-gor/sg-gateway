# SG-Gateway

**Самостоятельная веб-панель для установки и управления одним Ubuntu-сервером с Xray, AmneziaWG, Mihomo, WARP и безопасной маршрутизацией.**

![Версия](https://img.shields.io/badge/version-0.1.0--021-3b82f6)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Xray](https://img.shields.io/badge/Xray-v26.6.27-2563EB)
![systemd](https://img.shields.io/badge/deploy-native%20systemd-16A085)

> Текущая чистая GitHub-линия: **SG-Gateway 021** · приложение **`0.1.0-021`**.
> SG-Gateway — отдельный проект. В нём нет Controller, SG-Node и Cascade; код не смешивается с SG-Panel и SG-AWG-Panel.

## Что такое SG-Gateway

SG-Gateway разворачивает на одной Ubuntu EC2/VPS собственный VPN/proxy-сервер и даёт единый интерфейс для клиентов, подключений, маршрутизации, GeoFiles, WARP, HTTPS, резервных копий и диагностики.

```text
Клиент
  |
  +-- AmneziaWG UDP 585 --------------------------+
  |                                               |
  +-- Xray: Reality / XHTTP / Hysteria 2 --------+--> Routing --> Direct / WARP / Block --> Интернет
  |                                               |
  +-- Mihomo: Mieru / AnyTLS / TUIC v5 -----------+
```

Пользовательский трафик проходит через отдельные системные службы. Временная недоступность веб-панели не должна останавливать уже работающие подключения.

## Главное в SG-Gateway 021

- нативная установка на Ubuntu без Docker;
- одна самостоятельная панель на одном сервере;
- единый каталог клиентов и отдельные устройства;
- QR-коды, файлы конфигурации и SG Client subscription;
- безопасная проверка и применение конфигураций;
- резервная копия и rollback перед рискованными операциями;
- тёмная и светлая темы с единым оформлением страниц;
- установка, обновление и полное удаление напрямую из GitHub `main`.

## Подключения

### Xray Server

Поддерживаются четыре независимых профиля:

1. **VLESS Reality TCP** — XTLS Vision;
2. **VLESS XHTTP Reality** — XTLS Vision и VLESS Encryption;
3. **VLESS XHTTP TLS** — XTLS Vision, VLESS Encryption и HTTPS;
4. **Hysteria 2** — TLS, QUIC и Salamander FinalMask.

Сервер XHTTP остаётся в режиме `auto`, а клиентский режим выбирается отдельно. Для обоих XHTTP-профилей постоянно применяется клиентский профиль **XMUX для РФ**:

```json
{
  "maxConcurrency": 0,
  "maxConnections": 6,
  "cMaxReuseTimes": 0,
  "hMaxRequestTimes": "600-900",
  "hMaxReusableSecs": "1800-3000",
  "hKeepAlivePeriod": 0
}
```

XMUX добавляется только в клиентские ссылки, QR и subscriptions. Серверный inbound не меняется.

### AmneziaWG

- фиксированный внешний UDP-порт `585`;
- отдельные ключи и адреса устройств;
- DNS, MTU и параметры серверного профиля;
- сохранение и применение через системную службу.

### Mihomo

Один управляемый Mihomo Core обслуживает три независимых listener:

- **Mieru**;
- **AnyTLS**;
- **TUIC v5**.

Каждый listener включается отдельно. Раскрытие блока «Дополнительно» только показывает настройки и не включает протокол.

## Clients

- один клиент может иметь несколько устройств;
- каждое устройство получает собственные реквизиты;
- доступные профили выбираются отдельно;
- выдаются общая subscription, QR, загрузка файла и техническая ссылка;
- клиент и устройство можно отключить без удаления;
- карточки клиентов и устройств используют единый стиль панели.

## Routing и GeoFiles

Routing назначает реальные действия:

- `Direct`;
- `WARP`;
- `Block`.

GeoFiles работают связанной парой `geoip.dat` + `geosite.dat`. Поддерживаются:

- встроенная пара SG Client;
- Loyalsoldier;
- RunetFreedom;
- RoscomVPN;
- пользовательские HTTPS-адреса;
- загрузка двух файлов;
- локальные пути сервера.

Перед применением строится candidate-конфигурация и выполняется проверка Xray. Пользовательские правила не удаляются автоматически из-за отсутствующей geo-категории.

## HTTPS и безопасность

HTTPS включается из раздела **Security** после того, как домен направлен на публичный IPv4 сервера.

Привилегированная транзакция:

1. проверяет домен и DNS;
2. получает сертификат Let’s Encrypt;
3. создаёт резервную копию Nginx и TLS-state;
4. проверяет конфигурацию Nginx;
5. переключает публичный доступ на HTTPS;
6. проверяет backend и новый HTTPS-адрес;
7. выполняет автоматический rollback при ошибке.

Веб-процесс работает без root-прав и не читает закрытые файлы `/etc/letsencrypt` напрямую. Доступное панели состояние сертификата хранится отдельно.

## System, Maintenance и Help

Панель показывает:

- CPU, RAM, диск и процессы;
- состояние служб и подключений;
- резервные копии;
- диагностику и журналы;
- обновление Xray и приложения;
- справку по разделам и рабочим сценариям.

## Установка из GitHub

Используйте чистую Ubuntu EC2/VPS:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl tar gzip && curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-from-github.sh | sudo bash
```

Установщик определяет новую установку или обновление, создаёт страховочную копию, проверяет конфигурации и скрывает приватные данные в постоянном журнале.

Начальная установка работает по HTTP/IP. Домен и сертификат можно добавить позднее из панели.

## Обновление

Для обновления существующей SG-Gateway используется та же команда:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl tar gzip && curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-from-github.sh | sudo bash
```

Перед изменением сервера updater сохраняет управляемые файлы, SQLite, конфигурации и состояние служб. При ошибке выполняется откат.

## Полное удаление

```bash
curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/full-uninstall-ubuntu.sh | sudo bash
```

Подтверждение:

```text
DELETE SG-GATEWAY
```

Удаляются приложение, данные, управляемые службы, конфигурации Nginx, Xray, AmneziaWG, Mihomo, sing-box, WARP helper и правила UFW, созданные SG-Gateway. Общие пакеты Ubuntu намеренно сохраняются.

## Размещение файлов

```text
/opt/sg-gateway       приложение и Python-окружение
/etc/sg-gateway       конфигурация установки
/var/lib/sg-gateway   SQLite и runtime-state
/var/log/sg-gateway   журналы
```

Основные службы:

```text
sg-gateway.service
sg-hostd.service
xray.service
sg-gateway-awg.service
mihomo.service
sg-gateway-singbox.service
nginx.service
```

## Разработка и проверка

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
python -m compileall -q app hostd/sg_hostd tests
find . -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n
```

GitHub Actions является обязательной финальной проверкой каждого опубликованного изменения.

## Сборка автономного установщика 021

```bash
chmod +x build-run.sh
./build-run.sh
```

Результат:

```text
SG-Gateway-021-FULL-CLEAN-EC2-REBUILT.run
```

Дополнительные режимы:

```bash
./SG-Gateway-021-FULL-CLEAN-EC2-REBUILT.run --verify-only
./SG-Gateway-021-FULL-CLEAN-EC2-REBUILT.run --extract-only ./SG-Gateway-021-SOURCE
```

## Документация

- [Начало работы](docs/README.md)
- [Установка и обновление](docs/INSTALLATION.md)
- [Руководство пользователя](docs/USER-GUIDE.md)
- [Connections и клиентские профили](docs/CONNECTIONS.md)
- [Routing и GeoFiles](docs/ROUTING.md)
- [HTTPS и безопасность](docs/security.md)
- [Maintenance и диагностика](docs/MAINTENANCE.md)
- [Полное удаление](docs/UNINSTALL.md)

## Правила репозитория

- единственная активная ветка — `main`;
- SG-Gateway не смешивается с SG-Panel и SG-AWG-Panel;
- рабочая функциональность меняется только по подтверждённой причине;
- сгенерированные `.run`, ZIP, локальные базы, резервные копии и секреты в GitHub не коммитятся;
- `data/sg-gateway.sqlite` — единственная отслеживаемая чистая SQLite-база;
- новая версия назначается только после накопительного изменения и реальной проверки.
