# SG-Gateway 0.1.0-022.05 — LIVE publication

Дата публикации: **2026-08-15**.

## Принятая live-база

- VERSION: `0.1.0-022.05`
- live-validated commit: `9fbf42aea2bde80a99229de5661a93b6dce4f6c1`
- live-validated tree: `c482dc4f158dc1d61c2ba1d683a14e96d24dac68`
- live branch: `live-02205-accepted-20260815`
- stable snapshot: `stable-02205`
- release snapshot: `release-02205-live`
- next development branch: `dev-02206`

Live update завершился штатным сообщением `SG-Gateway safely updated`; rollback не сработал. Перед публикацией R4 development CI подтвердил **472 passed, 4 skipped**.

## Что публикуется

Публичная 022.05 сохраняет принятый VPN/runtime-контракт без изменений после live validation. Publication-слой меняет только release/build metadata, документацию, главный GitHub CI и генератор self-extracting `.run` пакета.

`build-run.sh` теперь берёт `VERSION` и `BUILD-ID` из текущего дерева, архивирует точный committed `HEAD`, проверяет `SOURCE-SHA256SUMS`, собирает self-extracting `.run`, повторно выполняет `--verify-only`, создаёт SHA256-файл и transfer ZIP.

## Линия обновлений

022.05 оставляет frozen update-channel `dev-02205`; эта ветка больше не используется для новой разработки. Новая работа начинается только в `dev-02206`. Это не даёт опубликованным 022.05-инсталляциям случайно перейти на будущую development-линию.
