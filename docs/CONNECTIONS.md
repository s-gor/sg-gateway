# Connections и клиентские профили

## AmneziaWG

SG-Gateway использует внешний UDP-порт `585`. Настройки сервера включают адрес, DNS, ключи и параметры профиля. Для каждого устройства создаётся отдельная клиентская конфигурация.

## Xray

### VLESS Reality TCP

Классический TCP/Reality-профиль с XTLS Vision.

### VLESS XHTTP Reality

Клиентская ссылка содержит XHTTP mode, VLESS Encryption и XMUX для РФ. Сервер остаётся в `auto`.

### VLESS XHTTP TLS

Требует готового HTTPS-домена. Клиентская ссылка содержит XHTTP mode, VLESS Encryption и тот же XMUX-профиль.

### Hysteria 2

Использует QUIC/UDP и TLS. Salamander FinalMask включается отдельно и проходит полную проверку candidate.

## XMUX для РФ

Профиль применяется постоянно к обоим XHTTP-профилям:

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

Эти значения добавляются в `extra.xmux` клиентских ссылок. Они не записываются в серверный inbound.

## Mihomo

Mieru, AnyTLS и TUIC v5 — независимые listener одного Mihomo Core. Галочка рядом с listener включает его. Раскрытая секция «Дополнительно» только показывает поля.

Mihomo размещён отдельным полноширинным блоком, чтобы три listener не сжимали поля друг друга.
