"""One Eye pass (roadmap, Agent 1 rules 2–4 and 10–12).

For each site: ask the posts sitemap (no cookie). The first time a site is seen, every address is recorded as seen and nothing
is read (the baseline). Later, an address not in `eye_seen` is new. New addresses are read slowly with my cookie, the two sites
in turn, the oldest first, at most `cap` pages for the pass. A block stops the pass at once. Nothing is printed on a quiet pass."""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field

from agents.eye import http, inbox, sentence, sitemap, store, tags
from agents.eye.extract import is_glossary, parse_post
from agents.eye.sites import SITES, Site
from shared import ai, notify

CAP = 80                   # pages per pass (Agent 1 rule 4)
GUARD = 200                # more new addresses than this in one pass → read none (my decision, 2026-10-11)
PAUSE_S = (20, 30)         # seconds between two requests
MAX_FAILS_IN_A_ROW = 3     # network errors, or pages whose body could not be found
COOKIE_WARN_AFTER = 5      # this many cut pages in a row with a cookie set → "the cookie has probably expired" (my decision, 2026-10-12)


class PassStopped(RuntimeError):
    """The pass ended early on purpose; the message goes to Telegram as an error."""


@dataclass
class Tally:
    read: int = 0
    text_missing: int = 0      # the page was cut (a gate block)
    glossary: int = 0
    gone: int = 0
    failed: int = 0
    baseline: int = 0
    waiting: int = 0           # new addresses left for the next pass
    note: str = ""


SENTENCES_PER_PASS = 120   # sentences written in one pass (the new posts of a pass are at most CAP; the rest are earlier failures)


@dataclass
class Result:
    tally: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)      # the AI stage: a problem worth a message
    sentences: int = 0
    tags_classified: int = 0
    tags_waiting: int = 0

    def message(self) -> str | None:
        """A quiet pass says nothing; a baseline, a gated page, a failure or a skipped site does."""
        lines = []
        for key, t in self.tally.items():
            name = SITES[key].name
            if t.baseline:
                lines.append(f"{name}: first run — {t.baseline:,} addresses recorded as seen, nothing read.")
            if t.text_missing:
                lines.append(f"{name}: {t.text_missing} page(s) were cut by the paywall (text_missing) of {t.read + t.text_missing} read.")
            if t.failed:
                lines.append(f"{name}: {t.failed} page(s) could not be fetched; they are tried again next pass.")
            if t.note:
                lines.append(f"{name}: {t.note}")
        lines += self.notes
        return notify.message("EYE · pass", lines) if lines else None


class _Pacer:
    def __init__(self, sleep, pause):
        self.sleep, self.pause, self.started = sleep, pause, False

    def wait(self) -> None:
        if self.started:
            self.sleep(self.pause(*PAUSE_S))
        self.started = True


def run_pass(conn, *, sites: dict | None = None, cookies: dict | None = None, fetch=None, sleep=time.sleep,
             pause=random.uniform, cap: int = CAP, guard: int = GUARD, accept_many: bool = False, ai_stage: bool = False,
             run=None, seclist: tags.SecList | None = None, skip=()) -> Result:
    sites = SITES if sites is None else sites
    sites = {key: site for key, site in sites.items() if key not in set(skip)}      # a skipped site is not touched at all
    cookies = {k: os.environ.get(s.cookie_env, "").strip() for k, s in sites.items()} if cookies is None else cookies
    fetch = http.fetch if fetch is None else fetch
    pacer = _Pacer(sleep, pause)
    result = Result({key: Tally() for key in sites})

    queues: dict[str, list[str]] = {}
    for key, site in sites.items():
        pacer.wait()
        try:
            entries = sitemap.posts(site, fetch(site.posts_sitemap, timeout=90).body)
        except http.Blocked as error:
            raise PassStopped(f"{site.name} blocked us: {error}. Nothing more was asked. Wait, then run it again.") from None
        except (http.FetchError, ValueError) as error:
            raise PassStopped(f"{site.name}: the sitemap could not be read: {error}") from None
        seen = store.known(conn, key)
        if not seen:
            store.add_baseline(conn, key, [e.url for e in entries])
            result.tally[key].baseline = len(entries)
            continue
        queues[key] = [e.url for e in sorted((e for e in entries if e.url not in seen), key=lambda e: (e.lastmod, e.url))]

    total_new = sum(len(q) for q in queues.values())
    if total_new > guard and not accept_many:
        raise PassStopped(
            f"Unusual number of new posts: {total_new} new addresses (the limit is {guard}). None was read. "
            "If the site is fine (for example the Air was off for days), run `python -m agents.eye --accept-many`."
        )

    for key in list(queues):
        if not cookies.get(key):
            result.tally[key].note = f"{sites[key].cookie_env} is not set in .env, so this site was not read."
            result.tally[key].waiting = len(queues.pop(key))

    taken, fails_in_a_row = 0, 0
    while taken < cap and any(queues.values()):
        for key in list(queues):
            if taken >= cap or not queues[key]:
                continue
            site, tally = sites[key], result.tally[key]
            url = queues[key].pop(0)
            taken += 1
            pacer.wait()
            try:
                answer = fetch(url, cookie=cookies[key])
            except http.Blocked as error:
                raise PassStopped(f"{site.name} blocked us: {error}. Nothing more was asked. Read so far this pass: "
                                  f"{sum(t.read + t.text_missing for t in result.tally.values())}.") from None
            except http.FetchError:
                tally.failed += 1
                fails_in_a_row = _fail(fails_in_a_row, site, "the network failed")
                continue
            if answer.status in (404, 410):
                store.record(conn, key, url, "gone")
                tally.gone += 1
                fails_in_a_row = 0
                continue
            if answer.status != 200:
                tally.failed += 1
                fails_in_a_row = _fail(fails_in_a_row, site, f"HTTP {answer.status}")
                continue
            post = parse_post(answer.text, site)
            if post.body_selector is None and not post.gated:
                tally.failed += 1      # not recorded: after a fix it is read again
                fails_in_a_row = _fail(fails_in_a_row, site, "the post body was not found; the page layout may have changed")
                continue
            fails_in_a_row = 0
            if is_glossary(post, site):
                store.record(conn, key, url, "glossary")
                tally.glossary += 1
            elif post.text_missing:
                store.record(conn, key, url, "text_missing", post)
                tally.text_missing += 1
            else:
                store.record(conn, key, url, "read", post)
                tally.read += 1

    for key, queue in queues.items():
        result.tally[key].waiting = len(queue)
    for key, site in sites.items():
        if cookies.get(key) and result.tally[key].text_missing and _cookie_looks_expired(conn, key):
            result.notes.append(f"{site.name}: the last {COOKIE_WARN_AFTER} pages in a row were cut by the paywall. The login cookie has "
                                f"probably expired and needs renewing (python -m agents.eye.set_cookie {key}).")
    if ai_stage:
        after_reading(conn, result, run=run, seclist=seclist)
    return result


def _cookie_looks_expired(conn, key: str) -> bool:
    """The newest COOKIE_WARN_AFTER pages that were read or cut are all cut: with a valid login that does not happen (my decision, 2026-10-12)."""
    rows = conn.execute("SELECT how FROM eye_seen WHERE site = ? AND how IN ('read', 'text_missing') ORDER BY seen_at DESC, rowid DESC LIMIT ?",
                        (key, COOKIE_WARN_AFTER)).fetchall()
    return len(rows) == COOKIE_WARN_AFTER and all(row[0] == "text_missing" for row in rows)


def after_reading(conn, result: Result, *, run=None, seclist: tags.SecList | None = None) -> None:
    """The AI stage, after the slow reading: the sentences, then the new tags, then the Inbox list. An AI problem never loses a page:
    the post is already saved, and the missing sentence or tag is tried again in the next pass."""
    written = []
    rows = conn.execute("SELECT id, site, title, url, full_text FROM articles WHERE sentence IS NULL AND text_missing = 0 "
                        "AND length(full_text) > 0 ORDER BY id LIMIT ?", (SENTENCES_PER_PASS,)).fetchall()
    for article_id, site, title, url, text in rows:
        try:
            line = sentence.write(title, text, run=run, conn=conn)
        except ai.AIError as error:
            result.notes.append(f"Sentences stopped: {error}. They are written in the next pass.")
            break
        except ValueError:
            line = ""          # two unusable answers: given up on this post ('' is not NULL, so it is not asked again)
        conn.execute("UPDATE articles SET sentence = ? WHERE id = ?", (line, article_id))
        conn.commit()
        if line:
            written.append({"site": site, "title": title, "sentence": line, "url": url})
    result.sentences = len(written)
    stats = tags.classify_new(conn, run, seclist=seclist)
    result.tags_classified, result.tags_waiting = stats.classified, stats.waiting
    if stats.note:
        result.notes.append(stats.note)
    inbox.append(written)


def _fail(count: int, site: Site, why: str) -> int:
    count += 1
    if count >= MAX_FAILS_IN_A_ROW:
        raise PassStopped(f"{site.name}: {MAX_FAILS_IN_A_ROW} pages in a row failed ({why}). The pass stopped; "
                          "the failed pages are tried again next pass.")
    return count
