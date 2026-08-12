from __future__ import annotations

import copy
import secrets
from typing import Any


SALAMANDER_MODE_NONE = "none"
# Compatibility contract: SG-Gateway stores "salamander" in DB and Xray
# FinalMask still uses type "salamander". Gecko is selected by packetSize.
SALAMANDER_MODE = "salamander"
SALAMANDER_MODES = (SALAMANDER_MODE_NONE, SALAMANDER_MODE)
SALAMANDER_MINIMUM_VERSION = "26.6.27"
SALAMANDER_PASSWORD_BYTES = 24
GECKO_CLIENT_MODE = "gecko"
GECKO_PACKET_SIZE = "512-1200"


class SalamanderError(ValueError):
    pass


def generate_password() -> str:
    """Return 24 cryptographically-random bytes as Base64URL without padding."""
    value = secrets.token_urlsafe(SALAMANDER_PASSWORD_BYTES)
    if len(value) < 32 or "=" in value:
        raise SalamanderError("Не удалось создать корректный пароль Gecko")
    return value


def normalise_mode(value: Any) -> str:
    mode = str(value or SALAMANDER_MODE_NONE).strip().lower()
    # Accept "gecko" from future callers, but keep the persisted/internal
    # representation stable for compatibility with existing 021/022 state.
    if mode == GECKO_CLIENT_MODE:
        return SALAMANDER_MODE
    if mode not in SALAMANDER_MODES:
        raise SalamanderError("Неизвестный режим обфускации Hysteria2")
    return mode


def password_ready(value: Any) -> bool:
    text = str(value or "").strip()
    return len(text) >= 16 and not any(char.isspace() for char in text)


def validate_password(value: Any) -> str:
    text = str(value or "").strip()
    if not password_ready(text):
        raise SalamanderError(
            "Пароль Gecko должен содержать не менее 16 символов без пробелов"
        )
    if len(text) > 256:
        raise SalamanderError("Пароль Gecko слишком длинный")
    return text


def version_key(value: Any) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in str(value or "").lstrip("v").split("."))
    except (TypeError, ValueError):
        return ()


def version_supported(installed: Any, minimum: str = SALAMANDER_MINIMUM_VERSION) -> bool:
    current = version_key(installed)
    required = version_key(minimum)
    if not current or not required:
        return False
    width = max(len(current), len(required))
    return current + (0,) * (width - len(current)) >= required + (0,) * (width - len(required))


def _contains_salamander(finalmask: dict[str, Any]) -> bool:
    udp = finalmask.get("udp")
    if not isinstance(udp, list):
        return False
    return any(
        isinstance(item, dict)
        and str(item.get("type") or "").strip().lower() == SALAMANDER_MODE
        for item in udp
    )


def finalmask_base(value: Any) -> dict[str, Any]:
    """Return a safe deep copy of the unmanaged/base FinalMask object."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SalamanderError("Существующий FinalMask Hysteria2 повреждён")
    result = copy.deepcopy(value)
    for key in ("tcp", "udp"):
        if key in result and not isinstance(result[key], list):
            raise SalamanderError(f"FinalMask {key} должен быть массивом")
    if "quicParams" in result and not isinstance(result["quicParams"], dict):
        raise SalamanderError("FinalMask quicParams должен быть объектом")
    return result


def ensure_base_has_no_salamander(value: Any) -> dict[str, Any]:
    base = finalmask_base(value)
    if _contains_salamander(base):
        raise SalamanderError(
            "В базовом FinalMask уже существует управляемый Salamander/Gecko слой. "
            "SG-Gateway не будет перезаписывать его автоматически."
        )
    return base


def merge_finalmask(base_value: Any, mode: Any, password: Any) -> dict[str, Any]:
    """Render managed Hysteria2 Gecko while preserving legacy DB semantics.

    Xray names the FinalMask primitive ``salamander``. Gecko is that primitive
    with ``packetSize`` enabled. SG-Gateway therefore keeps the historical
    database mode ``salamander`` but renders packetSize=512-1200 and exports
    the client-facing obfs name ``gecko``.

    Managed Gecko is exclusive for the UDP FinalMask path. Stored unmanaged
    UDP masks remain in state and are restored exactly when obfuscation is
    disabled. Non-UDP FinalMask fields remain active in both modes.
    """
    base = finalmask_base(base_value)
    selected = normalise_mode(mode)
    if selected == SALAMANDER_MODE_NONE:
        return base

    secret = validate_password(password)
    if _contains_salamander(base):
        raise SalamanderError(
            "Нельзя добавить управляемый Gecko поверх существующего Salamander/Gecko слоя"
        )

    base["udp"] = [
        {
            "type": SALAMANDER_MODE,
            "settings": {
                "password": secret,
                "packetSize": GECKO_PACKET_SIZE,
            },
        }
    ]
    return base


def safe_status(mode: Any, password: Any) -> dict[str, Any]:
    selected = normalise_mode(mode)
    configured = selected == SALAMANDER_MODE and password_ready(password)
    return {
        "mode": selected,
        "variant": GECKO_CLIENT_MODE if selected == SALAMANDER_MODE else SALAMANDER_MODE_NONE,
        "enabled": selected == SALAMANDER_MODE,
        "password_configured": configured,
        "password_mask": "•" * 32 if configured else "",
        "minimum_version": SALAMANDER_MINIMUM_VERSION,
        "packet_size": GECKO_PACKET_SIZE if selected == SALAMANDER_MODE else "",
    }
