# Документация SG-Gateway

Документация относится к линии **SG-Gateway 021** и версии приложения **`0.1.0-021`**.

## С чего начать

1. [Установка и обновление](INSTALLATION.md)
2. [Руководство пользователя](USER-GUIDE.md)
3. [Connections и клиентские профили](CONNECTIONS.md)
4. [Routing и GeoFiles](ROUTING.md)
5. [HTTPS и безопасность](security.md)
6. [Maintenance и диагностика](MAINTENANCE.md)
7. [Полное удаление](UNINSTALL.md)

## Разделы панели

```text
System       ресурсы, службы и состояние
Clients      клиенты, устройства, QR и subscriptions
Connections  AmneziaWG, Xray и Mihomo
Outbounds    Direct, WARP и Block
Routing      правила и GeoFiles
Maintenance  копии, журналы, обновления
Security     доступ, HTTPS и защита
Help         встроенная справка
```

## Главное правило

Любое изменение серверных подключений или Routing сначала проверяется. Применение выполняется только после успешной проверки candidate-конфигурации. Перед рискованными изменениями создаётся страховочная копия, а при ошибке выполняется rollback.
