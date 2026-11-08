"""One look: the gate, then the page sorter. python -m agents.pdf_reader"""

from __future__ import annotations

import fcntl
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from agents.pdf_reader import gate, paths, registry, sorter
from agents.pdf_reader.paths import PathsError
from agents.pdf_reader.registry import RegistryError

_USAGE = "usage: python -m agents.pdf_reader"
_TURKEY = ZoneInfo("Europe/Istanbul")


def _sorted_line(name: str, result: dict) -> str:
    counts = result["counts"]
    start = result["disclosure_start"]
    if start is None:
        where = "disclosures start not found"
    else:
        where = f"disclosures start p. {start['page']} ({start['found_by']})"
    return (
        f"sorted: {name} · {result['page_count']} pages · "
        f"content {counts['content']} (written {counts['content_written']}, scanned {counts['content_scanned']}) · "
        f"disclosure {counts['disclosure']} (read {counts['disclosure_read']}) · "
        f"{where} · invisible characters dropped {counts['dropped_invisible']}"
    )


def _sort_one(name: str, fingerprint: str, now: datetime) -> list[str]:
    work = paths.work_dir(fingerprint)
    if (work / "pages.json").is_file():
        return [f"waiting for step 3 (not built yet): {name}"]
    source = paths.new_dir() / name
    was_there = source.is_file()
    try:
        result = sorter.run(work, now)
    except Exception as error:
        count, gave_up = gate.record_attempt_failure(
            fingerprint, "sorter", f"{type(error).__name__}: {error}", now,
        )
        lines = [f"sorter failed (try {count} of {gate.MAX_ATTEMPTS}): {name} · {type(error).__name__}: {error}"]
        if gave_up and was_there and not source.is_file():
            lines.append(f"moved to Failed after 3 tries: {name}")
        return lines
    registry.append("sorted", fingerprint, now, name=name, page_count=result["page_count"])
    return [_sorted_line(name, result)]


def main(argv: list[str] | None = None, *, now: datetime | None = None, sleep=time.sleep) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv != []:
        print(_USAGE)
        return 2
    try:
        paths.ensure_dirs()
    except PathsError as error:
        print(str(error))
        return 2
    lock_path = paths.work_root() / "look.lock"
    lock_file = open(lock_path, "a")
    try:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another look is running; nothing was done.")
            return 0
        if now is None:
            now = datetime.now(timezone.utc)
        shown = now.astimezone(_TURKEY)
        print(f"PDF READER · look of {shown:%Y-%m-%d %H:%M} Turkey time")
        try:
            report = gate.look(now, sleep)
        except RegistryError as error:
            print(f"{error}; nothing was done.")
            return 1
        lines: list[str] = []
        for name, fingerprint, pages in report.queued:
            lines.append(f"queued: {name} ({pages} pages)")
            lines.extend(_sort_one(name, fingerprint, now))
        for name, fingerprint in report.in_progress:
            lines.extend(_sort_one(name, fingerprint, now))
        for old, new in report.source_changed:
            lines.append(f"source changed: {old} → {new}")
        for copy, original in report.duplicates_waiting:
            lines.append(f"duplicate, waits for the original {original}: {copy}")
        for name, dest in report.moved:
            lines.append(f"duplicate moved to {dest}: {name}")
        for name, reason, detail in report.failed:
            lines.append(f"failed ({reason}): {name} · {detail}")
        for name in report.waiting_sync:
            lines.append(f"waiting for Drive sync: {name}")
        for name in report.not_pdf:
            lines.append(f"not a PDF, left in New: {name}")
        for name in report.missing:
            lines.append(f"missing from New (queued earlier): {name}")
        if not lines:
            print("nothing new")
        else:
            print("\n".join(lines))
        return 0
    finally:
        lock_file.close()


if __name__ == "__main__":
    sys.exit(main())
