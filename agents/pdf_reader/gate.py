"""Step 1, the gate. It knows a PDF by its bytes and does not read the pages."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import pypdfium2

from agents.pdf_reader import files, paths, registry

MIN_AGE_SECONDS = 120
STABLE_WAIT_SECONDS = 5
MAX_ATTEMPTS = 3
_CHUNK = 1024 * 1024


@dataclass
class LookReport:
    queued: list[tuple[str, str, int]] = field(default_factory=list)
    in_progress: list[tuple[str, str]] = field(default_factory=list)
    source_changed: list[tuple[str, str]] = field(default_factory=list)
    duplicates_waiting: list[tuple[str, str]] = field(default_factory=list)
    moved: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str, str]] = field(default_factory=list)
    waiting_sync: list[str] = field(default_factory=list)
    not_pdf: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)


def candidates(folder: Path) -> tuple[list[Path], list[str]]:
    pdfs: list[Path] = []
    others: list[str] = []
    for path in sorted(folder.iterdir(), key=lambda item: item.name.casefold()):
        name = path.name
        if path.is_dir() or name.startswith(".") or name.startswith("~"):
            continue
        if path.suffix.lower() != ".pdf":
            others.append(name)
        else:
            pdfs.append(path)
    return pdfs, others


def _measure(path: Path) -> tuple[int, int, float, float]:
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_mtime, stat.st_ctime


def settled(files_in: list[Path], now: float, sleep=time.sleep) -> tuple[list[Path], list[Path]]:
    first: dict[Path, tuple[int, int, float, float]] = {}
    for path in files_in:
        try:
            first[path] = _measure(path)
        except FileNotFoundError:
            pass
    if files_in:
        sleep(STABLE_WAIT_SECONDS)
    ready: list[Path] = []
    waiting: list[Path] = []
    for path in files_in:
        if path not in first:
            continue
        try:
            size, mtime_ns, mtime, ctime = _measure(path)
        except FileNotFoundError:
            continue
        same = (first[path][0], first[path][1]) == (size, mtime_ns)
        old_enough = now - max(mtime, ctime) >= MIN_AGE_SECONDS
        if same and size > 0 and old_enough:
            ready.append(path)
        else:
            waiting.append(path)
    return ready, waiting


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def open_check(path: Path) -> tuple[str | None, int, str]:
    try:
        doc = pypdfium2.PdfDocument(str(path))
    except pypdfium2.PdfiumError as error:
        message = str(error)
        reason = "encrypted" if "password" in message.lower() else "broken"
        return reason, 0, message[:300]
    try:
        count = len(doc)
    finally:
        doc.close()
    if count == 0:
        return "broken", 0, "the file has no pages"
    try:
        with pdfplumber.open(path) as pdf:
            seen = len(pdf.pages)
    except Exception as error:
        return "broken", 0, f"{type(error).__name__}: {error}"[:300]
    if seen != count:
        return "broken", 0, f"page count differs: pdfium {count}, pdfplumber {seen}"
    return None, count, ""


def _move_copy(report: LookReport, records: list[dict], fp: str, path: Path, folder: Path, label: str, now: datetime) -> None:
    dest = files.move_unique(path, folder)
    records.append(registry.append(
        "duplicate_moved", fp, now, name=path.name, to=label, new_name=dest.name,
    ))
    report.moved.append((path.name, label))


def _accept_new(report: LookReport, records: list[dict], fp: str, first: Path, pages: int, now: datetime) -> None:
    size = first.stat().st_size
    paths.work_dir(fp).mkdir(parents=True, exist_ok=True)
    files.write_json(paths.work_dir(fp) / "queue.json", {
        "version": 1,
        "fingerprint": fp,
        "source_name": first.name,
        "size_bytes": size,
        "page_count": pages,
        "queued_at": files.utc_stamp(now),
    })
    records.append(registry.append(
        "queued", fp, now, name=first.name, size_bytes=size, page_count=pages,
    ))
    report.queued.append((first.name, fp, pages))


def _note_duplicate(report: LookReport, records: list[dict], fp: str, path: Path, original: str, now: datetime) -> None:
    if not registry.has_duplicate_note(records, fp, path.name):
        records.append(registry.append(
            "duplicate", fp, now, name=path.name, original_name=original,
        ))
    report.duplicates_waiting.append((path.name, original))


def look(now: datetime | None = None, sleep=time.sleep) -> LookReport:
    paths.ensure_dirs()
    records = registry.load()
    if now is None:
        now = datetime.now(timezone.utc)
    report = LookReport()
    pdfs, report.not_pdf = candidates(paths.new_dir())
    ready, waiting = settled(pdfs, now.timestamp(), sleep)
    report.waiting_sync = [path.name for path in waiting]
    groups: dict[str, list[Path]] = {}
    order: list[str] = []
    for path in ready:
        fp = fingerprint(path)
        if fp not in groups:
            order.append(fp)
            groups[fp] = []
        groups[fp].append(path)
    for fp in order:
        group = groups[fp]
        state = registry.status(records, fp)
        if state == "new":
            first, *rest = group
            reason, pages, detail = open_check(first)
            if reason:
                files.move_unique(first, paths.failed_dir())
                records.append(registry.append("failed", fp, now, name=first.name, reason=reason, detail=detail))
                report.failed.append((first.name, reason, detail))
                for copy in rest:
                    _move_copy(report, records, fp, copy, paths.failed_dir(), "Failed", now)
            else:
                _accept_new(report, records, fp, first, pages, now)
                for copy in rest:
                    _note_duplicate(report, records, fp, copy, first.name, now)
        elif state == "in_progress":
            src = registry.source_name(records, fp)
            by_name = {path.name: path for path in group}
            if src in by_name:
                source = by_name[src]
                copies = [path for path in group if path is not source]
            else:
                source = group[0]
                records.append(registry.append(
                    "source_changed", fp, now, old_name=src, name=source.name,
                ))
                queue = files.read_json(paths.work_dir(fp) / "queue.json")
                queue["source_name"] = source.name
                files.write_json(paths.work_dir(fp) / "queue.json", queue)
                report.source_changed.append((src, source.name))
                copies = group[1:]
            report.in_progress.append((source.name, fp))
            for copy in copies:
                _note_duplicate(report, records, fp, copy, source.name, now)
        elif state == "mailed":
            for path in group:
                _move_copy(report, records, fp, path, paths.done_dir(), "Done", now)
        elif state == "failed":
            for path in group:
                _move_copy(report, records, fp, path, paths.failed_dir(), "Failed", now)
    seen = {row["fingerprint"] for row in records}
    for fp in seen:
        if fp in groups or registry.status(records, fp) != "in_progress":
            continue
        name = registry.source_name(records, fp)
        if name and not (paths.new_dir() / name).exists():
            report.missing.append(name)
    return report


def record_attempt_failure(
    fingerprint: str, step: str, detail: str, now: datetime | None = None,
) -> tuple[int, bool]:
    if now is None:
        now = datetime.now(timezone.utc)
    records = registry.load()
    n = registry.attempts(records, fingerprint) + 1
    name = registry.source_name(records, fingerprint)
    text = detail[:300]
    registry.append(
        "attempt_failed", fingerprint, now, name=name, step=step, detail=text, attempt=n,
    )
    if n >= MAX_ATTEMPTS:
        if name and (paths.new_dir() / name).exists():
            files.move_unique(paths.new_dir() / name, paths.failed_dir())
        registry.append(
            "failed", fingerprint, now, name=name, reason="three_attempts", detail=text,
        )
        return n, True
    return n, False
