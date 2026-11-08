"""The fingerprint record. Lines are appended. The file is never rewritten or deleted."""

from __future__ import annotations

import json
import os
from datetime import datetime

from agents.pdf_reader.files import utc_stamp
from agents.pdf_reader.paths import registry_file

EVENTS = ("queued", "duplicate", "duplicate_moved", "source_changed", "attempt_failed", "failed", "sorted", "mailed")


class RegistryError(Exception):
    pass


def append(event: str, fingerprint: str, now: datetime, **fields) -> dict:
    if event not in EVENTS:
        raise ValueError(event)
    line = {"at": utc_stamp(now), "event": event, "fingerprint": fingerprint, **fields}
    path = registry_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return line


def load() -> list[dict]:
    path = registry_file()
    if not path.exists():
        return []
    records = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            raise RegistryError(f"registry line {n} is not valid JSON") from None
    return records


def status(records, fingerprint: str) -> str:
    events = [row["event"] for row in records if row["fingerprint"] == fingerprint]
    if "mailed" in events:
        return "mailed"
    if "failed" in events:
        return "failed"
    if "queued" in events:
        return "in_progress"
    return "new"


def attempts(records, fingerprint: str) -> int:
    return sum(1 for row in records if row["fingerprint"] == fingerprint and row["event"] == "attempt_failed")


def source_name(records, fingerprint: str) -> str | None:
    found = None
    for row in records:
        if row["fingerprint"] == fingerprint and row["event"] in ("queued", "source_changed"):
            found = row["name"]
    return found


def has_duplicate_note(records, fingerprint: str, name: str) -> bool:
    return any(
        row["fingerprint"] == fingerprint and row["event"] == "duplicate" and row["name"] == name
        for row in records
    )
