"""`Inbox/YYYY-MM-DD.md` — the Eye's daily list for me (Agent 1 rule 6; my decision, 2026-10-11): one file a day (Turkey date), each
pass appends a block: title, the one sentence, the address. It goes to Drive only; Telegram does not get it."""

from __future__ import annotations

from pathlib import Path

from agents.eye.sites import SITES
from shared import clock, drive


def append(items: list[dict], now=None) -> Path | None:
    """`items`: dicts with site (key), title, sentence, url. Returns the file, or None when there is nothing to add."""
    if not items:
        return None
    moment = now or clock.now_utc()
    local = clock.local(moment)
    folder = drive.inbox()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{clock.today_local(moment)}.md"
    text = "" if path.exists() else f"# Inbox · {clock.today_local(moment)}\n"
    text += f"\n## {local.strftime('%H:%M')} (Turkey time)\n"
    for item in items:
        site = SITES[item["site"]].name if item["site"] in SITES else item["site"]
        text += f"- {site} · **{item['title'] or '(no title)'}** — {item['sentence']} ({item['url']})\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)
    return path
