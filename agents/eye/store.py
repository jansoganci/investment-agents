"""The Eye's database calls: seen addresses (`eye_seen`) and the post itself (`articles`)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from agents.eye.extract import Post
from shared import clock


def known(conn, site_key: str) -> set[str]:
    return {row[0] for row in conn.execute("SELECT url FROM eye_seen WHERE site = ?", (site_key,))}


def add_baseline(conn, site_key: str, urls: list[str]) -> None:
    now = clock.utc_iso()
    conn.executemany(
        "INSERT OR IGNORE INTO eye_seen (url, site, seen_at, how) VALUES (?, ?, ?, 'baseline')",
        [(url, site_key, now) for url in urls],
    )
    conn.commit()


def utc_date(text: str | None) -> str | None:
    """The page writes its date with an offset (`+03:00`) or `Z`; the database keeps UTC."""
    if not text:
        return None
    try:
        moment = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return text
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return clock.utc_iso(moment.astimezone(timezone.utc))


def record(conn, site_key: str, url: str, how: str, post: Post | None = None) -> None:
    """One post done: its row in `articles` (unless it is a glossary post or gone) and its address in `eye_seen`, together."""
    now = clock.utc_iso()
    if post is not None:
        conn.execute(
            "INSERT OR IGNORE INTO articles (url, site, title, published_at, tags, full_text, read_deep, text_missing, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (url, site_key, post.title, utc_date(post.published_at), json.dumps(post.tags, ensure_ascii=False),
             post.text, 1 if post.text_missing else 0, now),
        )
    conn.execute("INSERT OR REPLACE INTO eye_seen (url, site, seen_at, how) VALUES (?, ?, ?, ?)", (url, site_key, now, how))
    conn.commit()
