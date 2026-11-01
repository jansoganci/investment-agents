"""The text a job prints. Our code never talks to Telegram: Hermes runs the job and delivers what it prints.

Format: a short title line in capitals, then plain lines. No output = no message.
All system output is in English (roadmap section 10.1).
"""

from __future__ import annotations

from shared import clock

MAX_LEN = 4096  # Telegram's limit for one message
CUT_NOTE = "… (cut; the full text is in Drive)"


def message(title: str, lines: list[str] | tuple[str, ...] = (), *, cut: bool = True) -> str:
    """`cut=False`: a long message is not cut; Hermes delivers it in parts with (n/N) labels (my decision, 2026-11-01)."""
    text = "\n".join([title, *lines])
    if cut and len(text) > MAX_LEN:
        text = text[: MAX_LEN - len(CUT_NOTE) - 1].rstrip() + "\n" + CUT_NOTE
    return text


def error(job: str, detail: str) -> str:
    return message(f"ERROR · {job}", [detail, f"Time: {clock.show(clock.now_utc())} (Turkey time)"])
