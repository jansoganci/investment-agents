"""uv run python -m shared.drive test

The step-0 test script (docs/AIR_SETUP.md, phase 7, tests 3 and 6): writes a dated file into `Investing/Inbox/`
and prints a short message. Scheduled hourly on the Air as a Hermes script-only job, the file must show up in
Drive on the phone and the message must arrive on Telegram.
"""

from __future__ import annotations

import sys

from shared import clock, drive, notify, runlog

USAGE = "usage: python -m shared.drive test"


def _test(_run) -> str:
    drive.ensure_folders()
    now = clock.local()
    name = f"drive-test-{now.strftime('%Y-%m-%d-%H%M')}.md"
    path = drive.inbox() / name
    path.write_text(
        "---\n"
        f"doc: Drive test\ndate: {now.strftime('%Y-%m-%d')}\npublish: no\n"
        "---\n\n"
        f"Written by `shared.drive test` at {now.strftime('%Y-%m-%d %H:%M')} (Turkey time).\n",
        encoding="utf-8",
    )
    return notify.message(
        "DRIVE TEST",
        [f"Wrote Inbox/{name} at {now.strftime('%H:%M')} (Turkey time).", "If you can read this on Telegram, the message path works."],
    )


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv != ["test"]:
        print(USAGE)
        return 2
    return runlog.job_main("drive_test", _test)


if __name__ == "__main__":
    sys.exit(main())
