from __future__ import annotations

from dataclasses import dataclass

from app.connections.geoip_country import lookup_country_code
from app.connections.settings import get_connection_settings

COUNTRY_NAMES = {
    "nl": "Нидерланды",
    "de": "Германия",
    "fi": "Финляндия",
    "fr": "Франция",
    "gb": "Великобритания",
    "pl": "Польша",
    "us": "США",
    "ca": "Канада",
    "sg": "Сингапур",
    "tr": "Турция",
    "il": "Израиль",
    "unknown": "Страна не выбрана",
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




def _country_for(settings) -> str:
    detected = lookup_country_code(settings.host)
    return detected if detected != "unknown" else "unknown"

def list_connections() -> list[ConnectionSummary]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT engine, COUNT(*) AS total
            FROM device_credentials
            GROUP BY engine
            """
        ).fetchall()

    counts = {row["engine"]: int(row["total"]) for row in rows}
    awg = get_connection_settings("amneziawg")
    xray = get_connection_settings("xray")
    mihomo = get_connection_settings("mihomo")

    return [
        ConnectionSummary(
            name="amneziawg",
            label="AmneziaWG",
            status="Configured" if awg.enabled else "Disabled",
            port=f"UDP {awg.port}",
            clients=counts.get("amneziawg", 0),
            note=f"Адрес: {awg.host}:{awg.port}",
            country_code=_country_for(awg),
            country_name=country_name(_country_for(awg)),
        ),
        ConnectionSummary(
            name="xray",
            label="Xray Reality",
            status="Configured" if xray.enabled else "Disabled",
            port=f"TCP {xray.port}",
            clients=counts.get("xray", 0),
            note=f"Адрес: {xray.host}:{xray.port}",
            country_code=_country_for(xray),
            country_name=country_name(_country_for(xray)),
        ),
        ConnectionSummary(
            name="mihomo",
            label="Mihomo Multi-Protocol",
            status="Configured" if mihomo.enabled else "Disabled",
            port=(
                f"TCP {mihomo.config.get('mieru_port', mihomo.port)} / "
                f"{mihomo.config.get('anytls_port', 8443)} · "
                f"UDP {mihomo.config.get('tuic_port', 10443)}"
            ),
            clients=counts.get("mihomo", 0),
            note=f"Адрес: {mihomo.host}; Mieru / AnyTLS / TUIC v5",
            country_code=_country_for(mihomo),
            country_name=country_name(_country_for(mihomo)),
        ),
    ]
