"""Times are stored in UTC and shown in Turkey time (roadmap section 5)."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from shared import config

LOCAL = ZoneInfo(config.settings()["timezone"])  # Europe/Istanbul


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime | None = None) -> str:
    """UTC timestamp for the database, e.g. 2026-10-04T20:15:03Z."""
    dt = (dt or now_utc()).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def local(dt: datetime | None = None) -> datetime:
    return (dt or now_utc()).astimezone(LOCAL)


def show(text_or_dt: str | datetime | None) -> str:
    """For people: '2026-10-04 23:15' in Turkey time."""
    if text_or_dt is None:
        return "—"
    dt = parse_utc(text_or_dt) if isinstance(text_or_dt, str) else text_or_dt
    return local(dt).strftime("%Y-%m-%d %H:%M")


def today_local(dt: datetime | None = None) -> str:
    return local(dt).strftime("%Y-%m-%d")
