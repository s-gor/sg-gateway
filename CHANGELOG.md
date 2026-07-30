# 0.1.0-021.7 — Clients onboarding and protocol grid

- The Clients page now explains that `sg-admin` is the automatically created first VPN client, not a Linux/system user and not a panel login.
- The `sg-admin` note is shown only while that client exists; it tells the administrator to create personal clients and that `sg-admin` can be deleted after verification.
- The new-client dialog contains exactly eight selectable VPN protocol cards in a stable 4 × 2 desktop grid: four Xray profiles on the first row, then AmneziaWG, Mieru, AnyTLS and TUIC v5.
- `SG Client` is no longer a selectable protocol card; its subscription is still requested automatically as a hidden service value.
- TLS-dependent cards remain in place when unavailable and show `Требуется HTTPS`.
- Based strictly on the accepted 0.1.0-021.4 line; rejected 021.5/021.5.1/021.6 experiments are not merged.

# 0.1.0-021.4 — Hysteria2 Salamander exclusive UDP FinalMask

- Salamander is now the only live `streamSettings.finalmask.udp` layer while enabled.
- Existing/stored Hysteria2 UDP FinalMask masks are preserved in SG-Gateway state but suppressed from the live Xray config while Salamander is active.
- Disabling Salamander restores the exact stored base UDP FinalMask.
- Non-UDP FinalMask fields such as `tcp` and `quicParams` remain preserved.
- Existing full-candidate Xray validation and transactional rollback remain unchanged.
- Captured working live reference: Hysteria2 on UDP 8446 with exactly one `salamander` UDP FinalMask layer.
- Panel update availability now uses one normal user-facing message; internal updater-baseline/bootstrap terminology is no longer shown in the panel or update job output.

# 0.1.0-021.3 — Client QR display fix

- QR-коды клиента и QR подписки теперь открываются как отдельное окно поверх страницы.
- Исправлено обрезание QR рамкой страницы Clients (`overflow:hidden`).
- Backend и содержимое QR не изменялись: исправлено именно отображение уже успешно сгенерированного QR.

# 0.1.0-021.2 — HTTPS, Salamander diagnostics and split runtime Apply

- HTTPS setup no longer assumes `proxy_cookie_flags` support.
- Nginx 1.19.3+ keeps `proxy_cookie_flags`; Ubuntu Nginx 1.18 uses a compatible `proxy_cookie_path` fallback with Secure, HttpOnly and SameSite=Lax.
- Existing successful Let’s Encrypt certificate is reused on retry; rollback behavior is unchanged.
- Hysteria2 Salamander diagnostics no longer try to read the root-only Xray config from the web process; safe runtime truth is obtained through privileged HostD without exposing the password.
- Connections → Mieru / AnyTLS / TUIC v5 now applies the real split runtime: Mieru to Mihomo, AnyTLS and TUIC v5 to sing-box.
- The full requested form is validated before Apply, so enabling AnyTLS/TUIC without credentials or HTTPS gives a real error instead of staying silently in «Не применено».
- AnyTLS/TUIC sing-box runtime now uses the applied server ports/TUIC ALPN and updates client export endpoint fields only after successful runtime validation/restart.

# Changelog

## 0.1.0-021.2 · Panel updater bootstrap fix

- исправлена первая проверка/обновление из GitHub main после чистой установки, когда `panel-state.json` ещё не создан;
- первое обновление без baseline разрешается только на строго более новую `VERSION`, с полным backup и последующей привязкой к точному commit SHA;
- GitHub main получает fallback через публичный Atom feed / curl, если REST API временно недоступен;
- уже привязанный baseline с локально изменённым кодом по-прежнему блокирует автообновление.

## 0.1.0-021.2

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
