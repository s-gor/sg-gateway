from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    environment: str
    host: str
    port: int
    data_dir: Path
    log_dir: Path
    hostd_url: str


def load_config() -> AppConfig:
    return AppConfig(
        environment=os.getenv("SG_GATEWAY_ENV", "development"),
        host=os.getenv("SG_GATEWAY_HOST", "127.0.0.1"),
        port=int(os.getenv("SG_GATEWAY_PORT", "8080")),
        data_dir=Path(os.getenv("SG_GATEWAY_DATA_DIR", "data")),
        log_dir=Path(os.getenv("SG_GATEWAY_LOG_DIR", "logs")),
        hostd_url=os.getenv("SG_GATEWAY_HOSTD_URL", "http://127.0.0.1:8090"),
    )