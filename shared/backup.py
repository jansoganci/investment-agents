"""uv run python -m shared.backup

The nightly copy of SQLite into `Investing/Backup/` with SQLite's own backup command (consistent even while
another job writes). Keeps the last 7 daily copies + the latest copy of each of the 4 weeks before them
(roadmap section 5). Only files named `investment-agents-YYYY-MM-DD.sqlite` are ever removed. Each copy is one
self-contained file, written under a temporary name first.
Prints nothing when all is well (no message); an error prints an error message for Telegram.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from shared import clock, config, drive, runlog
from shared import db as dbmod

PATTERN = re.compile(r"^investment-agents-(\d{4}-\d{2}-\d{2})\.sqlite$")


def file_name(day: date) -> str:
    return f"investment-agents-{day.isoformat()}.sqlite"


def date_of(name: str) -> date:
    return date.fromisoformat(PATTERN.match(name).group(1))


def to_keep(names: list[str], keep_daily: int, keep_weekly: int) -> list[str]:
    ours = sorted((n for n in names if PATTERN.match(n)), key=date_of, reverse=True)
    keep = ours[:keep_daily]
    weeks: list[tuple[int, int]] = []
    for n in ours[keep_daily:]:  # newest first, so the first one seen in a week is that week's latest copy
        week = date_of(n).isocalendar()[:2]
        if week in weeks:
            continue
        if len(weeks) == keep_weekly:
            break
        weeks.append(week)
        keep.append(n)
    return keep


def prune(folder: Path, keep_daily: int, keep_weekly: int) -> list[Path]:
    names = [p.name for p in folder.iterdir() if p.is_file()]
    keep = set(to_keep(names, keep_daily, keep_weekly))
    removed = []
    for n in names:
        if PATTERN.match(n) and n not in keep:
            (folder / n).unlink()
            removed.append(folder / n)
    return removed


def make_copy(day: date) -> Path:
    conn = dbmod.connect()
    try:
        return dbmod.copy_to(conn, drive.backup_dir() / file_name(day))
    finally:
        conn.close()


def _backup(_run) -> None:
    cfg = config.settings()["backup"]
    path = make_copy(date.fromisoformat(clock.today_local()))
    removed = prune(drive.backup_dir(), cfg["keep_daily"], cfg["keep_weekly"])
    print(f"Backup written: {path} · old copies removed: {len(removed)}", file=sys.stderr)
    return None


def main(argv: list[str] | None = None) -> int:
    return runlog.job_main("backup", _backup)


if __name__ == "__main__":
    sys.exit(main())
