from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agent.i18n import t


def _resolve_timezone(timezone_name: str) -> tuple[ZoneInfo, str]:
    candidate = str(timezone_name or "").strip() or "UTC"
    try:
        return ZoneInfo(candidate), candidate
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC"), "UTC"


def current_datetime(timezone_name: str, now: datetime | None = None) -> tuple[datetime, str]:
    timezone, resolved_name = _resolve_timezone(timezone_name)
    if now is None:
        return datetime.now(timezone), resolved_name
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone), resolved_name
    return now.astimezone(timezone), resolved_name


def build_current_date_response(timezone_name: str, now: datetime | None = None) -> dict[str, Any]:
    current, resolved_name = current_datetime(timezone_name, now)
    weekday_name = t(f"time.weekday_{current.weekday()}")
    clock_text = current.strftime("%H:%M")
    text = t(
        "time.date_response",
        weekday=weekday_name,
        day=current.day,
        month=current.month,
        year=current.year,
        clock=clock_text,
    )
    return {
        "text": text,
        "trace": {
            "timezone": resolved_name,
            "datetime": current.isoformat(timespec="seconds"),
            "weekday": weekday_name,
            "weekday_index": current.weekday(),
            "clock": clock_text,
        },
    }
