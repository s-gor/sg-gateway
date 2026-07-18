from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HelpTopic:
    slug: str
    title: str
    summary: str
    body: list[str]


TOPICS = [
    HelpTopic(
        slug="clients",
        title="Клиенты",
        summary="Клиент - это человек или устройство, а не отдельная техническая запись.",
        body=[
            "Создайте клиента, выберите доступ, а SG-Gateway подготовит нужные данные.",
            "Один клиент может иметь AmneziaWG, Xray Reality и будущую общую подписку.",
            "Клиента можно временно отключить без удаления его записей.",
        ],
    ),
    HelpTopic(
        slug="connections",
        title="Подключения",
        summary="В MVP есть два основных подключения: AmneziaWG и Xray Reality.",
        body=[
            "AmneziaWG выдает отдельный конфигурационный файл.",
            "Xray Reality выдает VLESS-ссылку для совместимого клиента.",
            "Новые клиенты получают параметры из страницы Подключения.",
        ],
    ),
    HelpTopic(
        slug="backups",
        title="Резервные копии",
        summary="Резервная копия сохраняет SQLite-базу панели.",
        body=[
            "Создавайте backup перед опасными изменениями.",
            "Перед восстановлением SG-Gateway сохраняет дополнительную страховочную копию.",
            "Backup можно скачать из раздела Обслуживание.",
        ],
    ),
    HelpTopic(
        slug="recovery",
        title="Recovery",
        summary="Recovery - минимальная аварийная страница.",
        body=[
            "Она показывает состояние системы и последние резервные копии.",
            "Она остается простой, даже если основной интерфейс станет богаче.",
            "Адрес страницы: /recovery.",
        ],
    ),
    HelpTopic(
        slug="diagnostics",
        title="Диагностика",
        summary="Диагностический отчет собирает состояние панели в один JSON-файл.",
        body=[
            "В отчет входят версия, health checks, клиенты, подключения, backup и журнал операций.",
            "Файл удобно прикладывать к обращению в поддержку.",
            "Скачивание диагностики записывается в журнал операций.",
        ],
    ),
]


def list_topics() -> list[HelpTopic]:
    return TOPICS


def get_topic(slug: str) -> HelpTopic | None:
    for topic in TOPICS:
        if topic.slug == slug:
            return topic
    return None
