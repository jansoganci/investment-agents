"""DeepSeek's web search (roadmap "Morning bulletin" 6; docs/BULLETIN_PLAN.md slice 1).

    hits = search.search("Brent crude oil", count=5, after="2026-10-27", conn=conn, run=run)
    uv run python -m shared.search "Brent crude oil"      5 hits with their dates, and the cost

`POST https://api.deepseek.com/v1/tools/search` with `DEEPSEEK_API_KEY` (the official docs, read for me by DeepSeek on 2026-10-28).
English sources only (`lang:en` in the query) and `after:YYYY-MM-DD` for a start date; the whole query, operators included, is at
most 128 characters. The answer has no cost field: a search that returns hits is counted at `pricing.deepseek_search_per_call` and
logged in `ai_calls` (job `search`, model `search`), so `/spend` and the monthly limit see it. An empty answer and a failed request
are not billed by DeepSeek and are not logged. The key is never printed.
"""

from __future__ import annotations

import json
import os
import sys
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from shared import ai, clock, config, redact
from shared import db as dbmod

URL = "https://api.deepseek.com/v1/tools/search"
KEY_ENV = "DEEPSEEK_API_KEY"
MAX_QUERY = 128
TIMEOUT_S = 30
STATUS_TEXT = {400: "the request was refused as malformed", 401: "the key was refused", 402: "the DeepSeek balance is empty",
               422: "a field of the request is not valid", 429: "too many requests (rate limit)", 500: "DeepSeek's server failed",
               503: "DeepSeek's server is overloaded"}


class SearchError(RuntimeError):
    """The search could not be made. The message never holds the key."""


@dataclass(frozen=True)
class Hit:
    title: str
    url: str
    site_name: str | None
    date: str | None          # publication time, UTC (RFC 3339), when DeepSeek knows it
    snippet: str              # ~100–200 characters, for display
    summary: str              # ~600–800 characters, for a model
    score: float | None       # `rerank_score`, 0–3; 1.5 or more = a good match
    authority: int | None     # 0–4, -1 unknown; 3 or more = an authoritative source


def clean_url(url: str) -> str:
    """The address without tracking parameters (`utm_source=…`, `srnd=…`): shorter and as good."""
    parts = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if not k.lower().startswith(("utm_", "srnd"))]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


_PLAIN_URL = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")


def usable_url(url: str | None) -> bool:
    """False for an address that cannot be opened: empty, not plain ASCII, or shortened by the search ("...", "…", a dot-leader look-alike).
    DeepSeek shortens some addresses (seen 2026-10-29); a strict check catches every look-alike of the dots."""
    return bool(url) and bool(_PLAIN_URL.match(url)) and ".." not in url


def build_query(query: str, after: str | None = None, english: bool = True) -> str:
    """The query with its operators. Too long (or empty) → SearchError, before anything is sent."""
    text = " ".join(query.split())
    if not text:
        raise SearchError("the search query is empty")
    parts = [text] + (["lang:en"] if english else []) + ([f"after:{after}"] if after else [])
    full = " ".join(parts)
    if len(full) > MAX_QUERY:
        raise SearchError(f"the search query is {len(full)} characters with its operators; DeepSeek takes at most {MAX_QUERY}")
    return full


def _post(body: dict, key: str, timeout: float = TIMEOUT_S) -> tuple[int, bytes]:
    """(HTTP status, body). Replaced in tests."""
    request = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SearchError(f"DeepSeek search could not be reached ({type(error).__name__})") from None


def _error_text(status: int, raw: bytes) -> str:
    reason = STATUS_TEXT.get(status, "an unexpected answer")
    try:
        message = (json.loads(raw).get("error") or {}).get("message")
    except (ValueError, AttributeError):
        message = None
    return f"DeepSeek search: HTTP {status}, {reason}" + (f" ({redact.clean(str(message))[:200]})" if message else "")


def _hit(item: dict) -> Hit | None:
    url = (item.get("url") or "").strip()
    if not url:
        return None
    score, authority = item.get("rerank_score"), item.get("authority")
    return Hit(title=(item.get("title") or "").strip(), url=url, site_name=item.get("site_name"), date=item.get("date"),
               snippet=(item.get("snippet") or "").strip(), summary=(item.get("summary") or "").strip(),
               score=float(score) if isinstance(score, (int, float)) else None,
               authority=int(authority) if isinstance(authority, int) else None)


def price() -> float:
    return float((config.settings().get("pricing") or {}).get("deepseek_search_per_call", 0.00075))


def search(query: str, *, count: int = 5, after: str | None = None, english: bool = True, conn=None, run=None) -> list[Hit]:
    """Hits for `query`, best first, as DeepSeek orders them. `after` = YYYY-MM-DD (or YYYY). Raises SearchError."""
    if not 1 <= count <= 50:
        raise SearchError("count must be 1–50")
    full = build_query(query, after, english)
    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        raise SearchError(f"{KEY_ENV} is not set")
    own = conn is None
    conn = conn or dbmod.connect()
    try:
        limit = (config.settings().get("budget") or {}).get("ai_monthly_max_usd")
        spent = ai.month_spend(conn)
        if limit is not None and spent >= limit:
            raise SearchError(f"the monthly AI limit is reached (${spent:.2f} of ${limit}); nothing was sent")
        status, raw = _post({"query": full, "count": count}, key)
        if status != 200:
            raise SearchError(_error_text(status, raw))
        try:
            items = json.loads(raw).get("results")
        except (ValueError, AttributeError):
            raise SearchError("DeepSeek search answered something that is not JSON") from None
        if not isinstance(items, list):
            raise SearchError("DeepSeek search answered without a `results` list")
        hits = [h for h in (_hit(i) for i in items if isinstance(i, dict)) if h]
        if hits:
            ai.log_reply(conn, run, ai.Reply("", "deepseek", "search", None, None, price(), "search"))
        return hits
    finally:
        if own:
            conn.close()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print('usage: python -m shared.search "your query"')
        return 2
    try:
        hits = search(argv[0])
    except (SearchError, dbmod.DatabaseMissing) as exc:
        print(f"SEARCH · failed\n{exc}")
        return 1
    lines = [f"SEARCH · {len(hits)} hit(s) · {clock.show(clock.now_utc())} (Turkey time)"]
    for n, h in enumerate(hits, 1):
        when = h.date[:10] if h.date else "no date"
        lines.append(f"{n}. {h.title} — {h.site_name or '?'} · {when} · score {h.score}\n   {h.url}")
    lines.append(f"Cost: ${price() if hits else 0:.5f} (an empty answer is free)")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
