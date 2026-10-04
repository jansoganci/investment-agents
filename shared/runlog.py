"""Every job writes one `runs` row: start, end, `ok` / `error`, dollars (roadmap section 3, "Rules that prevent spending").

    with runlog.run("prices") as r:
        r.add_cost(0.01)

The row is written as `running` at the start (so `/status` sees it) and closed at the end.
"""

from __future__ import annotations

import sys
import traceback
from contextlib import contextmanager
from typing import Callable

from shared import clock, notify
from shared import db as dbmod


class Run:
    def __init__(self, run_id: int):
        self.id = run_id
        self.cost_usd = 0.0

    def add_cost(self, usd: float) -> None:
        self.cost_usd += float(usd)


@contextmanager
def run(job: str):
    conn = dbmod.connect()
    try:
        cur = conn.execute(
            "INSERT INTO runs (job, started_at, status) VALUES (?, ?, 'running')", (job, clock.utc_iso())
        )
        conn.commit()
        r = Run(cur.lastrowid)
        try:
            yield r
        except BaseException as exc:
            conn.execute(
                "UPDATE runs SET ended_at=?, status='error', cost_usd=?, error=? WHERE id=?",
                (clock.utc_iso(), r.cost_usd, f"{type(exc).__name__}: {exc}", r.id),
            )
            conn.commit()
            raise
        conn.execute(
            "UPDATE runs SET ended_at=?, status='ok', cost_usd=? WHERE id=?", (clock.utc_iso(), r.cost_usd, r.id)
        )
        conn.commit()
    finally:
        conn.close()


def job_main(job: str, work: Callable[[Run], str | None]) -> int:
    """Run a job by hand or from Hermes: print its message; on an error print an error message and return 1."""
    try:
        with run(job) as r:
            text = work(r)
    except Exception as exc:  # noqa: BLE001 — every error must reach Telegram
        print(notify.error(job, f"{type(exc).__name__}: {exc}"))
        traceback.print_exc(file=sys.stderr)
        return 1
    if text:
        print(text)
    return 0
