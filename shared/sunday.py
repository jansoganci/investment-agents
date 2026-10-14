"""The Sunday chain (roadmap section 3, "Sunday order"): Counter → agent 2 → agent 3 → agent 4 → agent 3's drop-alert check → the summary. A step that fails is
reported and the next ones still run. One message at the end (the summary); the agents' own messages are not sent separately.

    uv run python -m shared.sunday              Hermes runs it on Sunday 09:00 Turkey time (docs/SCHEDULE.md)
    uv run python -m shared.sunday --day 2026-10-11
"""

from __future__ import annotations

import sys

from shared import clock, runlog, summary
from shared import db as dbmod

STEPS = ("counter", "research", "analysis", "portfolio", "drop_alerts")


def run_chain(day: str | None = None, sources=None) -> list[str]:
    """Runs the five steps (the last is agent 3 checking the drop alerts), builds and saves the summary; returns its lines."""
    from agents.analysis import run as analysis
    from agents.counter import count
    from agents.portfolio import run as portfolio
    from agents.research import run as research

    day = day or clock.today_local()
    errors: list[str] = []
    texts: dict[str, str | None] = {}

    def step(name, fn):
        try:
            with runlog.run(name) as r:
                conn = dbmod.connect()
                try:
                    texts[name] = fn(conn, r)
                finally:
                    conn.close()
        except Exception as exc:  # noqa: BLE001 — one failing step must not stop the week
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            texts[name] = None

    def count_step(conn, r):
        count.count(conn)          # stored in `counts`; the summary reads the table, so there is no text to keep

    step("counter", count_step)
    step("research", lambda conn, r: research.weekly(conn, sources, day, r))
    step("analysis", lambda conn, r: analysis.weekly(conn, sources, day, use_ai=True, run=r))
    step("portfolio", lambda conn, r: portfolio.weekly(conn, day))
    # Portfolio writes the pending drop-alert signals; agent 3 checks them against the latest filing right after (audit 2026-10-14, #4)
    step("drop_alerts", lambda conn, r: analysis.drop_alerts(conn, sources, day, run=r))
    errors += [line for line in (texts.get("research") or "").splitlines() if line.startswith("Not researched")]

    conn = dbmod.connect()
    try:
        agent_3 = "\n\n".join(t for t in (texts.get("analysis"), texts.get("drop_alerts")) if t) or None
        lines = summary.build(conn, day, portfolio_text=texts.get("portfolio"), analysis_text=agent_3, errors=errors)
    finally:
        conn.close()
    try:
        summary.save(day, lines)
    except Exception as exc:  # noqa: BLE001 — a Drive problem must not hide the message
        lines.append(f"(the summary could not be saved to Drive: {exc})")
    return lines


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    day = None
    if argv[:1] == ["--day"] and len(argv) == 2:
        day = argv[1]
    elif argv:
        print("usage: python -m shared.sunday [--day YYYY-MM-DD]")
        return 2
    return runlog.job_main("sunday", lambda _run: summary.message(run_chain(day)))


if __name__ == "__main__":
    sys.exit(main())
