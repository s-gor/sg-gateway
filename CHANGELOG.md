# Changelog

## 0.1.0-021.1

- Connections: runtime status now reflects the real split engines: Mieru from Mihomo, AnyTLS and TUIC v5 from sing-box.
- The panel reads safe listener truth through privileged HostD without weakening root-only runtime configuration permissions.
- Runtime state (Работает/Ошибка/Выключен) is separated from pending form changes, so a working listener is no longer mislabeled «Не применено».

## 0.1.0-021

Первый стабильный публичный выпуск SG-Gateway.

- Нативная установка на Ubuntu без Docker.
- Xray: VLESS Reality TCP, VLESS XHTTP Reality, VLESS XHTTP TLS и Hysteria 2.
- AmneziaWG, Mihomo/Mieru, sing-box (AnyTLS и TUIC v5) и WARP.
- Клиенты, устройства, ссылки, QR-коды и единая SG Client subscription.
- Routing и транзакционное применение парных GeoFiles с family-aware системными правилами, сохранением пользовательских правил и автоматическим rollback.
- HTTPS с Let’s Encrypt и отдельным привилегированным HostD.
- Резервные копии, диагностика и независимые обновления панели и runtime-компонентов.
- Vendored runtime-комплект из шести проверяемых core-архивов для воспроизводимой чистой установки.
- Mihomo/Mieru готов к работе сразу после чистой установки и управляется из общей панели.
- Простое обновление GeoFiles: выбрать источник → проверить → обновить; подробная инструкция содержит реальные скриншоты.
