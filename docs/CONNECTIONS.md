# Connections и клиентские профили

## AmneziaWG

SG-Gateway использует один серверный AmneziaWG-профиль. Настройки сервера включают адрес, DNS, ключи и параметры профиля. Для каждого устройства создаётся отдельная клиентская конфигурация.

## Xray

### VLESS Reality TCP

TCP/Reality-профиль с XTLS Vision.

### VLESS XHTTP Reality

Клиентская ссылка содержит XHTTP mode и VLESS Encryption. XMUX настраивается общим клиентским параметром для обоих XHTTP-профилей.

### VLESS XHTTP TLS

Требует готового HTTPS-домена. Клиентская ссылка содержит XHTTP mode и VLESS Encryption. XMUX использует тот же общий выбранный режим.

### Hysteria 2

Использует QUIC/UDP и TLS. Salamander FinalMask настраивается отдельно и проверяется перед применением.

## XMUX для XHTTP

По умолчанию выбран **Xray Auto**: SG-Gateway не добавляет `extra.xmux`, и клиент использует штатные значения установленного Xray.

Администратор может выбрать один из режимов:

- **Xray Auto** — рекомендуется, без навязанных значений;
- **Standard** — совместимый пресет SG-Panel;
- **Для РФ — уменьшенный** — совместимый пресет SG-Panel;
- **Ручной** — собственные значения или диапазоны для всех полей XMUX.

Standard:

```json
{
  "maxConnections": "2-4",
  "cMaxReuseTimes": "300-600",
  "hMaxRequestTimes": "1000-2000",
  "hMaxReusableSecs": "1200-2400",
  "hKeepAlivePeriod": 600
}
```

Для РФ — уменьшенный:

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

Положительные `maxConnections` и `maxConcurrency` одновременно запрещены. Любой выбранный XMUX добавляется только в клиентский `extra.xmux` и не записывается в серверный inbound.

## Mihomo и sing-box

- Mieru обслуживается Mihomo;
- AnyTLS и TUIC v5 обслуживаются отдельным sing-box.

Каждый движок имеет собственное runtime-состояние, а панель объединяет их результаты в одном интерфейсе. Выключенный профиль не выдаётся клиентам как доступный, при этом сохранённые реквизиты остаются в базе для повторного включения.
