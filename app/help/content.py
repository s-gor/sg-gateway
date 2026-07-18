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
        slug="system",
        title="System",
        summary="Read the current panel health, runtime mode and service readiness.",
        body=[
            "Use System for a quick overview before changing clients or connection endpoints.",
            "Health checks come from the same diagnostics used by the status API.",
            "Open Maintenance from this page when you need logs, backups or the full JSON report.",
        ],
    ),
    HelpTopic(
        slug="clients",
        title="Clients",
        summary="A client is a person or device, not a separate low-level engine record.",
        body=[
            "Create one client and choose whether it should receive AmneziaWG, Xray Reality, or both.",
            "The client detail page provides downloads, QR codes and the planned SG Client subscription.",
            "Disable a client to stop access without deleting the record and generated profiles.",
        ],
    ),
    HelpTopic(
        slug="connections",
        title="Connections",
        summary="Connection settings define the endpoints used in newly generated client profiles.",
        body=[
            "AmneziaWG produces a WireGuard-compatible configuration file.",
            "Xray Reality produces a VLESS link for compatible clients.",
            "Update hosts, ports, country labels and public keys before issuing production client access.",
        ],
    ),
    HelpTopic(
        slug="routing",
        title="Routing",
        summary="Routing shows the effective traffic paths built from the configured engines.",
        body=[
            "The Routing page is read-only: it summarizes what clients will receive from Connections.",
            "AmneziaWG uses DNS, allowed networks and keepalive settings from the stored engine config.",
            "Xray Reality uses the endpoint, SNI, public key and short ID from the stored engine config.",
        ],
    ),
    HelpTopic(
        slug="maintenance",
        title="Maintenance",
        summary="Backups, health checks, diagnostics and the operation log live here.",
        body=[
            "Create a backup before risky changes such as endpoint rotation or restore tests.",
            "Download diagnostics when you need a machine-readable support report.",
            "The operation log records client, connection, backup and diagnostic actions.",
        ],
    ),
    HelpTopic(
        slug="security",
        title="Security",
        summary="Review panel authentication, bind address exposure and recovery access.",
        body=[
            "The panel redirects unauthenticated users to the login page.",
            "Set SG_GATEWAY_ADMIN_PASSWORD to a strong value before exposing the panel outside localhost.",
            "Use a trusted private network or HTTPS reverse proxy for production access.",
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
