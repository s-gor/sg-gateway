from __future__ import annotations

from typing import Any, Mapping


XHTTP_XMUX_MODE_AUTO = "auto"
XHTTP_XMUX_MODE_STANDARD = "standard"
XHTTP_XMUX_MODE_REDUCED = "reduced"
XHTTP_XMUX_MODE_EXPERT = "expert"
XHTTP_XMUX_MODES = (
    XHTTP_XMUX_MODE_AUTO,
    XHTTP_XMUX_MODE_STANDARD,
    XHTTP_XMUX_MODE_REDUCED,
    XHTTP_XMUX_MODE_EXPERT,
)
XHTTP_XMUX_MODE_OPTIONS = (
    {
        "value": XHTTP_XMUX_MODE_AUTO,
        "title": "Xray Auto",
        "note": "Рекомендуется: SG-Gateway не передаёт extra.xmux и использует штатные значения текущего Xray.",
    },
    {
        "value": XHTTP_XMUX_MODE_STANDARD,
        "title": "Standard",
        "note": "Пресет SG-Panel для обычных сетей.",
    },
    {
        "value": XHTTP_XMUX_MODE_REDUCED,
        "title": "Для РФ — уменьшенный",
        "note": "Сохранённый совместимый пресет SG-Panel для ручного выбора.",
    },
    {
        "value": XHTTP_XMUX_MODE_EXPERT,
        "title": "Ручной",
        "note": "Пользователь задаёт параметры XMUX самостоятельно.",
    },
)

# Compatibility presets copied from SG-Panel. Neither preset is forced.
XHTTP_XMUX_STANDARD = {
    "maxConnections": "2-4",
    "cMaxReuseTimes": "300-600",
    "hMaxRequestTimes": "1000-2000",
    "hMaxReusableSecs": "1200-2400",
    "hKeepAlivePeriod": 600,
}
XHTTP_XMUX_REDUCED = {
    "maxConcurrency": 0,
    "maxConnections": 6,
    "cMaxReuseTimes": 0,
    "hMaxRequestTimes": "600-900",
    "hMaxReusableSecs": "1800-3000",
    "hKeepAlivePeriod": 0,
}

XHTTP_XMUX_RANGE_FIELDS = (
    "maxConcurrency",
    "maxConnections",
    "cMaxReuseTimes",
    "hMaxRequestTimes",
    "hMaxReusableSecs",
)
XHTTP_XMUX_FIELDS = XHTTP_XMUX_RANGE_FIELDS + ("hKeepAlivePeriod",)


class XmuxError(ValueError):
    pass


def normalise_mode(value: Any) -> str:
    mode = str(value or XHTTP_XMUX_MODE_AUTO).strip().lower()
    if mode not in XHTTP_XMUX_MODES:
        raise XmuxError("Некорректный режим XMUX")
    return mode


def _non_negative_int(value: Any, label: str) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise XmuxError(f"{label}: требуется целое число не меньше 0") from exc
    if number < 0:
        raise XmuxError(f"{label}: значение не может быть отрицательным")
    return number


def normalise_range(value: Any, label: str) -> int | str:
    if isinstance(value, int):
        if value < 0:
            raise XmuxError(f"{label}: значение не может быть отрицательным")
        return value
    text = str(value or "").strip()
    if not text:
        raise XmuxError(f"{label}: значение не задано")
    if "-" not in text:
        return _non_negative_int(text, label)
    parts = text.split("-")
    if len(parts) != 2:
        raise XmuxError(f"{label}: диапазон должен иметь вид 2-4")
    left = _non_negative_int(parts[0], label)
    right = _non_negative_int(parts[1], label)
    if left > right:
        raise XmuxError(f"{label}: начало диапазона больше конца")
    return f"{left}-{right}"


def _positive(value: Any) -> bool:
    if isinstance(value, int):
        return value > 0
    text = str(value or "").strip()
    if not text:
        return False
    if "-" in text:
        try:
            return int(text.split("-", 1)[1]) > 0
        except ValueError:
            return False
    try:
        return int(text) > 0
    except ValueError:
        return False


def validate_conflicts(xmux: Mapping[str, Any]) -> None:
    if _positive(xmux.get("maxConnections")) and _positive(xmux.get("maxConcurrency")):
        raise XmuxError(
            "XMUX не допускает одновременно положительные maxConnections и maxConcurrency"
        )


def normalise_expert(value: Any, *, require_non_empty: bool = False) -> dict[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise XmuxError("Ручной XMUX должен быть объектом")
    result: dict[str, Any] = {}
    for key in XHTTP_XMUX_RANGE_FIELDS:
        if key not in value or str(value.get(key) if value.get(key) is not None else "").strip() == "":
            continue
        result[key] = normalise_range(value.get(key), key)
    if "hKeepAlivePeriod" in value and str(value.get("hKeepAlivePeriod") if value.get("hKeepAlivePeriod") is not None else "").strip() != "":
        result["hKeepAlivePeriod"] = _non_negative_int(value.get("hKeepAlivePeriod"), "hKeepAlivePeriod")
    validate_conflicts(result)
    if require_non_empty and not result:
        raise XmuxError("Для ручного XMUX задайте хотя бы один параметр")
    return result


def resolve(config: Mapping[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    try:
        mode = normalise_mode(config.get("xhttp_xmux_mode"))
    except XmuxError:
        mode = XHTTP_XMUX_MODE_AUTO
    try:
        expert = normalise_expert(config.get("xhttp_xmux_expert"))
    except XmuxError:
        expert = {}

    if mode == XHTTP_XMUX_MODE_STANDARD:
        effective: dict[str, Any] | None = dict(XHTTP_XMUX_STANDARD)
    elif mode == XHTTP_XMUX_MODE_REDUCED:
        effective = dict(XHTTP_XMUX_REDUCED)
    elif mode == XHTTP_XMUX_MODE_EXPERT:
        effective = dict(expert) if expert else None
    else:
        # Native Xray mode: omit extra.xmux entirely.
        effective = None
    return mode, expert, effective


def from_form(form: Any, current_config: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    current_mode, current_expert, _ = resolve(current_config)
    mode = normalise_mode(form.get("xhttp_xmux_mode", current_mode))
    expert = dict(current_expert)
    if mode == XHTTP_XMUX_MODE_EXPERT:
        raw = {key: form.get(f"xhttp_xmux_{key}", "") for key in XHTTP_XMUX_FIELDS}
        expert = normalise_expert(raw, require_non_empty=True)
    return mode, expert
