from __future__ import annotations

from dataclasses import dataclass

from app.connections.settings import get_connection_settings

COUNTRY_NAMES = {
    "nl": "Netherlands",
    "de": "Germany",
    "fi": "Finland",
    "fr": "France",
    "gb": "United Kingdom",
    "pl": "Poland",
    "us": "United States",
    "ca": "Canada",
    "sg": "Singapore",
    "tr": "Turkey",
    "il": "Israel",
    "unknown": "Country not selected",
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
            status="Configured" if awg.enabled else "Disabled",
            port=f"UDP {awg.port}",
            clients=counts.get("amneziawg", 0),
            note=f"Endpoint: {awg.host}:{awg.port}",
            country_code=normalize_country_code(awg.config.get("country_code")),
            country_name=country_name(awg.config.get("country_code")),
        ),
        ConnectionSummary(
            name="xray",
            label="Xray Reality",
            status="Configured" if xray.enabled else "Disabled",
            port=f"TCP {xray.port}",
            clients=counts.get("xray", 0),
            note=f"Endpoint: {xray.host}:{xray.port}",
            country_code=normalize_country_code(xray.config.get("country_code")),
            country_name=country_name(xray.config.get("country_code")),
        ),
    ]
