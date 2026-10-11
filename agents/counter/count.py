"""The counting (roadmap, Agent 1B rules 1–6). Reads `articles` (their tags) and `tags` (what each tag is), writes `counts`.

A post is counted once for an entity however many of its tags point to it. Only `confirmed` tags count; waiting and unclassified
tags are only counted for the note. The 7 days are counted on the post's published date."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from shared import clock, config

KINDS = ("stock", "non_us", "commodity", "sector")


def cfg() -> dict:
    c = dict((config.settings().get("counter") or {}))
    c.setdefault("window_days", 7)
    c.setdefault("long_days", 30)
    c.setdefault("top", 10)
    c.setdefault("card_mention_bar", 6)
    c.setdefault("mention_points", [3, 6])
    return c


def mentions_points(posts: int, bars: list[int] | None = None) -> int:
    """Agent 2's `mentions` criterion: 1–2 posts → 0, 3–5 → 1, 6+ → 2 (the bars are in settings.yaml)."""
    low, high = bars or cfg()["mention_points"]
    return 2 if posts >= high else 1 if posts >= low else 0


@dataclass
class Entry:
    kind: str
    key: str
    label: str
    posts_7d: int
    posts_30d: int
    has_card: bool = False
    rank: int | None = None
    points: int | None = None


@dataclass
class Result:
    run_at: str
    to_day: str
    entries: list = field(default_factory=list)
    waiting_tags: int = 0          # tags in the window that wait for my /tag
    unclassified_tags: int = 0     # tags in the window the Eye has not classified yet
    posts_in_window: int = 0

    def of(self, kind: str) -> list[Entry]:
        return [e for e in self.entries if e.kind == kind]


def _entity(tag: dict) -> tuple[str, str] | None:
    """(kind, key) of a confirmed tag, or None when it is not something we count."""
    kind = tag["kind"]
    if kind == "company":
        if tag["us_listed"] == 1 and tag["maps_to"]:
            return "stock", tag["maps_to"].upper()
        if tag["us_listed"] == 0:
            return "non_us", (tag["maps_to"] or tag["tag"])
    elif kind in ("commodity", "sector") and tag["maps_to"]:
        return kind, tag["maps_to"]
    return None


def count(conn, now: datetime | None = None, write: bool = True) -> Result:
    c = cfg()
    now = now or clock.now_utc()
    since7 = clock.utc_iso(now - timedelta(days=c["window_days"]))
    since30 = clock.utc_iso(now - timedelta(days=c["long_days"]))
    result = Result(run_at=clock.utc_iso(now), to_day=clock.today_local(now))

    cur = conn.execute("SELECT tag, kind, maps_to, us_listed, status FROM tags")
    known = {r[0]: dict(zip(("tag", "kind", "maps_to", "us_listed", "status"), r)) for r in cur}
    cards = {r[0].upper(): r[1] for r in conn.execute("SELECT ticker, company FROM stocks")}

    posts7: dict = defaultdict(set)
    posts30: dict = defaultdict(set)
    names: dict = defaultdict(Counter)
    waiting, unclassified, window_posts = set(), set(), set()
    rows = conn.execute(
        "SELECT a.id, COALESCE(a.published_at, a.created_at) AS day, j.value FROM articles a, json_each(a.tags) j "
        "WHERE COALESCE(a.published_at, a.created_at) >= ?", (since30,))
    for article_id, day, name in rows:
        recent = day >= since7
        if recent:
            window_posts.add(article_id)
        tag = known.get(name)
        if tag is None:
            if recent:
                unclassified.add(name)
            continue
        if tag["status"] == "waiting":
            if recent:
                waiting.add(name)
            continue
        entity = _entity(tag)
        if entity is None:
            continue
        posts30[entity].add(article_id)
        if recent:
            posts7[entity].add(article_id)
            names[entity][name] += 1

    for (kind, key), ids in posts7.items():
        label = sorted(names[(kind, key)].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        entry = Entry(kind, key, label, len(ids), len(posts30[(kind, key)]))
        if kind in ("commodity", "sector"):
            entry.label = key              # show "copper", not the Turkish tag that pointed to it
        if kind == "stock":
            entry.has_card = key in cards
            entry.label = cards.get(key) or label
        result.entries.append(entry)

    for kind in KINDS:
        ranked = [e for e in result.of(kind) if not e.has_card]
        ranked.sort(key=lambda e: (-e.posts_7d, -e.posts_30d, e.key))
        for i, e in enumerate(ranked, 1):
            e.rank = i
            if kind == "stock":
                e.points = mentions_points(e.posts_7d, c["mention_points"])
    result.entries.sort(key=lambda e: (KINDS.index(e.kind), e.rank is None, e.rank or 0, -e.posts_7d, e.key))
    result.waiting_tags, result.unclassified_tags, result.posts_in_window = len(waiting), len(unclassified), len(window_posts)

    if write:
        conn.executemany(
            "INSERT INTO counts (run_at, kind, key, label, posts_7d, posts_30d, rank, has_card, points, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(result.run_at, e.kind, e.key, e.label, e.posts_7d, e.posts_30d, e.rank, int(e.has_card), e.points, result.run_at)
             for e in result.entries])
        conn.commit()
    return result


def latest(conn) -> Result | None:
    """The latest stored run (what agent 2 and `--show` read). The notes about tags are not stored, so they are 0 here."""
    run_at = conn.execute("SELECT max(run_at) FROM counts").fetchone()[0]
    if run_at is None:
        return None
    result = Result(run_at=run_at, to_day=clock.today_local(clock.parse_utc(run_at)))
    for kind, key, label, p7, p30, rank, card, points in conn.execute(
            "SELECT kind, key, label, posts_7d, posts_30d, rank, has_card, points FROM counts WHERE run_at = ? "
            "ORDER BY id", (run_at,)):
        result.entries.append(Entry(kind, key, label, p7, p30, bool(card), rank, points))
    return result
