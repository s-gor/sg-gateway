from __future__ import annotations

from dataclasses import dataclass

from app.connections.settings import get_connection_settings

COUNTRY_NAMES = {
    "nl": "Нидерланды", "de": "Германия", "fi": "Финляндия", "fr": "Франция",
    "gb": "Великобритания", "pl": "Польша", "us": "США", "ca": "Канада",
    "sg": "Сингапур", "tr": "Турция", "il": "Израиль", "unknown": "Страна не выбрана",
}

def normalize_country_code(value: str | None) -> str:
    code = (value or "unknown").strip().lower()
    return code if code in COUNTRY_NAMES else "unknown"

def country_name(code: str | None) -> str:
    return COUNTRY_NAMES.get(normalize_country_code(code), COUNTRY_NAMES["unknown"])
from app.db import connect


@dataclass(frozen=True)
class ConnectionSummary:
    name: str
    label: str
    status: str
    port: str
    clients: int
    note: str
    country_code: str
    country_name: str


def list_connections() -> list[ConnectionSummary]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT engine, COUNT(*) AS total
            FROM client_deployments
            GROUP BY engine
            """
        ).fetchall()

    counts = {row["engine"]: int(row["total"]) for row in rows}
    awg = get_connection_settings("amneziawg")
    xray = get_connection_settings("xray")

    return [
        ConnectionSummary(
            name="amneziawg",
            label="AmneziaWG",
            status="Настроено" if awg.enabled else "Отключено",
            port=f"UDP {awg.port}",
            clients=counts.get("amneziawg", 0),
            note=f"Адрес: {awg.host}:{awg.port}",
            country_code=normalize_country_code(awg.config.get("country_code")),
            country_name=country_name(awg.config.get("country_code")),
        ),
        ConnectionSummary(
            name="xray",
            label="Xray Reality",
            status="Настроено" if xray.enabled else "Отключено",
            port=f"TCP {xray.port}",
            clients=counts.get("xray", 0),
            note=f"Адрес: {xray.host}:{xray.port}",
            country_code=normalize_country_code(xray.config.get("country_code")),
            country_name=country_name(xray.config.get("country_code")),
        ),
    ]
