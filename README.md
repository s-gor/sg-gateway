# SG-Gateway

**Лёгкая и быстрая веб-панель для личного и семейного VPN.**

> **Один сервер. Одна панель. Семейный VPN без серверной акробатики.**

![Версия](https://img.shields.io/badge/version-0.1.0--021-3b82f6)
![Ubuntu](https://img.shields.io/badge/Ubuntu-native-E95420?logo=ubuntu&logoColor=white)
![Xray](https://img.shields.io/badge/Xray-supported-2563EB)
![AmneziaWG](https://img.shields.io/badge/AmneziaWG-supported-6D5BD0)
![Mihomo](https://img.shields.io/badge/Mihomo-supported-8B5CF6)
![sing-box](https://img.shields.io/badge/sing--box-supported-0EA5E9)
![WARP](https://img.shields.io/badge/WARP-supported-F38020?logo=cloudflare&logoColor=white)
![systemd](https://img.shields.io/badge/deploy-systemd-16A085)
![HTTPS](https://img.shields.io/badge/HTTPS-Let%27s_Encrypt-003A70?logo=letsencrypt&logoColor=white)

SG-Gateway устанавливается на **один самостоятельный Ubuntu-сервер** и превращает его в готовый VPN-шлюз с удобным веб-интерфейсом.

Он предназначен для дома, семьи и небольшой группы доверенных пользователей. Здесь нет Controller, SG-Nodes, Cluster, Cascade, распределённой базы серверов и ручного редактора полного JSON.

**Gateway — это просто выход в интернет. Без квантовой механики.**

Установили панель, создали клиентов и устройства, получили ссылки, QR-коды и подписки — пользуетесь.

### System — состояние сервера

![System — ресурсы и состояние](docs/screenshots/system.png)

## Две дороги

### Хочу установить и пользоваться

Продолжайте читать этот `README.md`. Здесь есть назначение панели, поддерживаемые подключения, установка, обновление и удаление.

### Хочу понимать, что происходит внутри

Откройте [техническое устройство SG-Gateway](docs/TECHNICAL.md): архитектура, XTLS Vision, VLESS Encryption, XMUX, службы, порты, HTTPS, Routing, GeoFiles и сохранность данных.

## Для кого создан SG-Gateway

SG-Gateway подходит, когда нужен:

- собственный VPN на одном VPS или EC2;
- доступ для семьи и близких;
- несколько устройств у каждого человека;
- современные профили Xray;
- AmneziaWG и дополнительные подключения;
- понятная маршрутизация;
- HTTPS, резервные копии и диагностика;
- управление без ручной сборки серверных JSON-конфигураций.

Для сети из нескольких серверов, SG-Nodes, Cluster и Cascade существует отдельный большой проект **SG-Panel**.

> **SG-Panel — для сложной инфраструктуры.
> SG-Gateway — для дома, семьи и спокойной жизни.**

## Что поддерживается

### Connections — общий экран

![Connections — доступные подключения](docs/screenshots/connections.png)

### Xray

SG-Gateway поддерживает современные профили Xray:

- **VLESS Reality TCP + XTLS Vision**;
- **VLESS XHTTP Reality + XTLS Vision + VLESS Encryption + XMUX для РФ**;
- **VLESS XHTTP TLS + XTLS Vision + VLESS Encryption + HTTPS + XMUX для РФ**;
- **Hysteria 2 + TLS + Salamander FinalMask**.

Панель сама создаёт серверные конфигурации, проверяет их перед применением и формирует клиентские ссылки. Ручное редактирование полного JSON не требуется.

![Настройки профилей Xray](docs/screenshots/xray-settings.png)

### AmneziaWG

Поддерживаются:

- сервер AmneziaWG;
- фиксированный внешний UDP-порт `585`;
- отдельные ключи и адреса устройств;
- клиентские конфигурации;
- управление службой из панели;
- совместимость с клиентами AmneziaVPN и AmneziaWG.

![Настройки AmneziaWG](docs/screenshots/amneziawg.png)

### Mihomo и sing-box

Рабочая архитектура разделена по движкам:

- **Mieru** обслуживается Mihomo;
- **AnyTLS** обслуживается отдельным sing-box;
- **TUIC v5** обслуживается отдельным sing-box.

Эти дополнительные движки применяются независимо и управляются из общей панели SG-Gateway.

![Mieru, AnyTLS и TUIC v5](docs/screenshots/extra-protocols.png)

### Cloudflare WARP

WARP используется как отдельный outbound. Routing решает, какой трафик отправить через `Direct`, `WARP` или `Block`.

WARP находится среди выходов, где ему и положено быть, а не изображает из себя отдельную философскую школу маршрутизации.

![WARP Outbound](docs/screenshots/warp-outbound.png)

## Клиенты и устройства

В SG-Gateway используется простая модель:

```text
Клиент
  └── Устройства
      ├── Телефон
      ├── Ноутбук
      └── Телевизор
```

Каждое устройство может получить собственные:

- UUID и реквизиты доступа;
- наборы разрешённых профилей;
- ссылку подключения;
- QR-код;
- файл конфигурации;
- персональную SG Client subscription.

Клиента или отдельное устройство можно временно отключить без удаления.

### Clients — список и карточка клиента

| Список клиентов | Карточка клиента |
| --- | --- |
| ![Список клиентов](docs/screenshots/clients.png) | ![Карточка клиента](docs/screenshots/client-card.png) |

### Добавление устройства

| Основные параметры | Выбор подключений |
| --- | --- |
| ![Добавление устройства](docs/screenshots/add-device.png) | ![Выбор подключений устройства](docs/screenshots/device-connections.png) |

## Routing и GeoFiles

Панель управляет направлениями:

- `Direct`;
- `WARP`;
- `Block`.

Поддерживаются доменные и IP-правила, готовые наборы и пользовательские правила.

GeoFiles работают парой `geoip.dat` + `geosite.dat`. Доступны встроенные и внешние источники, пользовательские HTTPS-адреса, загрузка файлов и локальные пути сервера.

Перед применением SG-Gateway строит будущую конфигурацию и проверяет её через Xray. Несовместимая Geo-категория блокирует применение, но пользовательские правила не удаляются автоматически.

![Routing и GeoFiles](docs/screenshots/routing.png)

## HTTPS и безопасность

HTTPS включается из раздела **Security** после направления домена на публичный IPv4 сервера.

Панель:

1. проверяет домен и DNS;
2. получает сертификат Let’s Encrypt;
3. создаёт резервную копию текущей конфигурации;
4. проверяет Nginx;
5. переключает панель на HTTPS;
6. проверяет backend и внешний адрес;
7. подтверждает рабочее состояние HTTPS.

Веб-процесс работает без root-прав. Привилегированные операции выполняет отдельная служба HostD.

| Security | Сертификат и режим доступа |
| --- | --- |
| ![Security](docs/screenshots/security.png) | ![Состояние сертификата](docs/screenshots/certificate-status.png) |

## Обслуживание

В панели доступны:

- состояние ресурсов и служб;
- журналы;
- диагностика;
- резервные копии;
- восстановление;
- обновление компонентов;
- проверка Xray;
- полное удаление SG-Gateway.

Диагностика показывает состояние основных служб и компонентов в понятном виде.

| Maintenance | Обновление компонентов |
| --- | --- |
| ![Maintenance](docs/screenshots/maintenance.png) | ![Обновление компонентов](docs/screenshots/updates.png) |

## А где подсчёт трафика?

Персонального подсчёта трафика клиентов пока нет.

SG-Gateway создавался для семейного VPN, а не для домашнего биллинга и вечернего расследования:

> «Кто за три дня потратил 280 гигабайт и почему снова виноват телевизор?»

Мы посмотрим, насколько индивидуальная статистика действительно нужна пользователям. Если функция окажется востребованной, она может появиться позднее как необязательная возможность.

> **Без учёта семейных гигабайтов — для сохранения мира в доме.**

## Чего здесь намеренно нет

SG-Gateway не является уменьшенной копией всей SG-Panel. В нём намеренно нет:

- Controller и SG-Nodes;
- Cluster и Cascade;
- управления группой VPS;
- распределённой базы клиентов;
- переноса клиентов между серверами;
- ручного редактора полного JSON;
- биллинга, тарифов и квот;
- обязательного персонального учёта трафика;

Это не список забытых функций. Это границы проекта.

## Установка

Используйте чистую Ubuntu EC2/VPS:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl tar gzip && curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-from-github.sh | sudo bash
```

После установки панель доступна по адресу, показанному установщиком. Начальная настройка может выполняться по HTTP и IP; домен и HTTPS добавляются позднее из раздела `Security`.

## Первые шаги

1. Откройте панель и войдите.
2. Проверьте состояние сервера на странице `System`.
3. Настройте нужные профили в `Connections`.
4. Создайте клиента и его устройства.
5. Получите ссылки, QR-коды или subscription.
6. При необходимости настройте `WARP`, `Routing` и `GeoFiles`.
7. Подключите домен и HTTPS.

## Обновление

Для обновления используется та же команда:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl tar gzip && curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/install-from-github.sh | sudo bash
```

Updater сохраняет управляемые данные и резервную копию текущего состояния перед обновлением.

## Полное удаление

```bash
curl -fsSL https://raw.githubusercontent.com/s-gor/sg-gateway/main/deploy/full-uninstall-ubuntu.sh | sudo bash
```

Подтверждение:

```text
DELETE SG-GATEWAY
```

Удаляются приложение, данные и управляемые SG-Gateway службы и конфигурации. Общие пакеты Ubuntu намеренно сохраняются.

## Документация

Встроенный раздел **Help** повторяет тот же рабочий порядок: System → Clients → Connections → Routing → Maintenance → Security.

![Help — встроенная справка SG-Gateway](docs/screenshots/help.png)

### Для пользователя

- [Начало работы](docs/README.md)
- [Установка и обновление](docs/INSTALLATION.md)
- [Руководство пользователя](docs/USER-GUIDE.md)
- [Connections и клиентские профили](docs/CONNECTIONS.md)
- [Routing и GeoFiles](docs/ROUTING.md)
- [HTTPS и безопасность](docs/security.md)
- [Maintenance и диагностика](docs/MAINTENANCE.md)
- [Полное удаление](docs/UNINSTALL.md)

### Для понимающего пользователя

- [Техническое устройство SG-Gateway](docs/TECHNICAL.md)

**Один сервер. Одна панель. Нормальный выход в интернет.**
