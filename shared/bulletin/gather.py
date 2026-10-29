"""Gathering the bulletin's raw material (docs/BULLETIN_PLAN.md slice 3). Code only: no model is called here.

    pack = gather.gather(conn, now=None, run=None)

A `Pack` holds numbered pieces the writer (slice 4) may cite and the number check can look into:

    P<n>  a post of the Eye (both sites) in the window; n = `articles.id`
    W<n>  a hit of a DeepSeek web search (one per stock I hold or watch, one per interest topic)
    F<n>  a new SEC filing of one of my stocks
    E<n>  the next earnings date of one of my stocks (Yahoo)

and, for each stock I hold or watch, the 3 "things that would break the thesis" from its card. The window is "since the last
bulletin": the previous weekday's bulletin time (Monday → Friday), so Monday covers the weekend. A search that fails is a note in
`pack.notes`, never an error; the rest of the bulletin goes on without it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from shared import clock, config, drive, search
from shared.prices import yahoo
from shared.sec import FORMS

# 8-K items in plain words (SEC's own item numbers). 9.01 (exhibits) alone is no news.
EIGHT_K = {"1.01": "entered into a material agreement", "1.02": "ended a material agreement", "1.03": "bankruptcy or receivership",
           "2.01": "completed an acquisition or a sale of assets", "2.02": "reported its results",
           "2.03": "took on a new financial obligation", "2.04": "a debt obligation was accelerated",
           "2.05": "announced exit or restructuring costs", "2.06": "recorded a material impairment",
           "3.01": "received a delisting notice", "3.02": "sold unregistered shares", "3.03": "changed the rights of shareholders",
           "4.01": "changed its auditor", "4.02": "said earlier financial statements should no longer be relied on",
           "5.01": "a change in control", "5.02": "a director or officer left or joined",
           "5.03": "changed its bylaws", "5.07": "reported a shareholder vote", "7.01": "made a public disclosure",
           "8.01": "reported another event"}
STOP_ON = ("is not set", "monthly AI limit", "HTTP 401", "HTTP 402")   # a search error that every later search would repeat


@dataclass(frozen=True)
class Piece:
    id: str
    kind: str                     # post | web | filing | earnings
    title: str
    text: str                     # what the writer sees; the number check looks here
    site: str = ""                # emtia | dragonomi | the web site | sec | yahoo
    when: str | None = None       # UTC time (posts, web, filings) or the date (earnings)
    url: str | None = None
    topic: str = ""               # web: the stock or interest this search was for
    tickers: tuple = ()           # my stocks this piece is about
    data: dict = field(default_factory=dict)   # filing: form, filed, items · earnings: date — the render writes its Turkish lines from this


@dataclass(frozen=True)
class StockInfo:
    ticker: str
    company: str
    held: bool
    thesis_date: str | None
    breaks: tuple                 # the card's 3 "things that would break the thesis" (empty when the card has none yet)


@dataclass
class Pack:
    window_start: str             # UTC
    window_end: str
    stocks: list = field(default_factory=list)
    posts: list = field(default_factory=list)
    web: list = field(default_factory=list)
    filings: list = field(default_factory=list)
    earnings: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    searches: int = 0

    def pieces(self) -> dict[str, Piece]:
        return {p.id: p for p in self.posts + self.web + self.filings + self.earnings}


def cfg() -> dict:
    c = dict(config.settings().get("bulletin") or {})
    c.setdefault("max_searches", 25)
    c.setdefault("post_chars", 3000)
    c.setdefault("full_posts", 40)
    c.setdefault("search_count", 5)
    c.setdefault("earnings_days", 45)
    c.setdefault("interests", [])
    return c


# --- the window ---------------------------------------------------------------------------------------------------------

def window_start(now: datetime | None = None) -> datetime:
    """The bulletin time of the last weekday before today (Turkey date): Tuesday → Monday, Monday → Friday."""
    now = now or clock.now_utc()
    hour, minute = (int(x) for x in str(config.settings().get("hours", {}).get("bulletin", "08:15")).split(":"))
    day = date.fromisoformat(clock.today_local(now)) - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=clock.LOCAL)


# --- my stocks and their theses -----------------------------------------------------------------------------------------

def breaks_of(text: str) -> tuple[str | None, tuple]:
    """(date of the newest thesis, its 3 breaks) from a card's text."""
    from agents.analysis import card

    found = card.last_thesis(text)
    if not found:
        return None, ()
    date_, thesis = found
    if "What would break it:" not in thesis:
        return date_, ()
    tail = thesis.split("What would break it:", 1)[1]
    items = re.findall(r"^\s*\d+\.\s+(.+)$", tail, flags=re.M)
    return date_, tuple(x.strip() for x in items[:3])


def my_stocks(conn) -> list[StockInfo]:
    """Stocks I hold first, then the ones I watch; each with the breaks of its card's thesis."""
    rows = conn.execute("SELECT ticker, company, in_portfolio FROM stocks WHERE in_portfolio = 'yes' OR status = 'watching' "
                        "ORDER BY (in_portfolio = 'yes') DESC, ticker").fetchall()
    out = []
    for ticker, company, held in rows:
        path = drive.find_card(ticker)
        thesis_date, breaks = breaks_of(path.read_text(encoding="utf-8")) if path else (None, ())
        out.append(StockInfo(ticker, company or ticker, held == "yes", thesis_date, breaks))
    return out


# --- posts --------------------------------------------------------------------------------------------------------------

def _tickers_by_tag(conn, mine: set[str]) -> dict[str, str]:
    """display name of a confirmed company tag → ticker, for my stocks only."""
    rows = conn.execute("SELECT tag, maps_to FROM tags WHERE kind = 'company' AND status = 'confirmed' AND maps_to IS NOT NULL")
    return {tag: ticker.upper() for tag, ticker in rows if ticker.upper() in mine}


def posts(conn, since: str, mine: set[str], c: dict | None = None) -> list[Piece]:
    """The Eye's posts published since `since` (UTC). The first `full_posts` — those about my stocks first, then the newest — come
    with up to `post_chars` of their text; the rest with title, tags and the one sentence only."""
    c = c or cfg()
    by_tag = _tickers_by_tag(conn, mine)
    rows = conn.execute("SELECT id, site, url, title, COALESCE(published_at, created_at), tags, sentence, full_text, text_missing "
                        "FROM articles WHERE COALESCE(published_at, created_at) >= ? ORDER BY 5 DESC, id DESC", (since,)).fetchall()
    items = []
    for article_id, site, url, title, when, tags_json, sentence, full_text, missing in rows:
        try:
            tags = [t for t in json.loads(tags_json or "[]") if isinstance(t, str)]
        except ValueError:
            tags = []
        tickers = tuple(sorted({by_tag[t] for t in tags if t in by_tag}))
        items.append((bool(tickers), article_id, site, url, title or "", when, tags, sentence or "", full_text or "", bool(missing), tickers))
    # who gets the full text: my stocks' posts first, then the newest (the rows are already newest first)
    full = {i[1] for i in sorted(items, key=lambda i: not i[0])[:c["full_posts"]]}
    out = []
    for _about_mine, article_id, site, url, title, when, tags, sentence, full_text, missing, tickers in items:
        lines = [title, f"Tags: {', '.join(tags)}" if tags else "", sentence]
        if article_id in full:
            lines.append("(the site cut this post for non-members: only the title and tags are known)" if missing
                         else full_text[:c["post_chars"]])
        out.append(Piece(f"P{article_id}", "post", title, "\n".join(x for x in lines if x), site, when, url, tickers=tickers))
    return out


# --- SEC filings and earnings dates -------------------------------------------------------------------------------------

def filings(stocks: list[StockInfo], ciks: dict[str, str], since: str, submissions=None) -> tuple[list[Piece], list[str]]:
    """New 10-K / 10-Q / 20-F and 8-K filings of my stocks accepted by SEC since `since`. Returns (pieces, notes)."""
    from shared import sec

    submissions = submissions or sec.submissions
    pieces, notes = [], []
    for s in stocks:
        cik = ciks.get(s.ticker)
        if not cik:
            continue
        try:
            recent = (submissions(cik).get("filings") or {}).get("recent") or {}
        except Exception as exc:  # noqa: BLE001 — one stock's SEC error must not stop the rest
            notes.append(f"SEC could not be asked for {s.ticker}: {type(exc).__name__}")
            continue
        forms = recent.get("form") or []
        # SEC lists are as long as `form`; a list SEC left out is read as empty values
        columns = [(recent.get(k) or []) + [None] * (len(forms) - len(recent.get(k) or []))
                   for k in ("form", "filingDate", "acceptanceDateTime", "items", "accessionNumber", "primaryDocument")]
        for form, filed, accepted, items, accession, document in zip(*columns):
            moment = (accepted or "")[:19]
            new = (moment + "Z" >= since) if moment else (filed or "") >= since[:10]
            if not new:
                continue
            if form in FORMS:
                text = f"{s.ticker} filed a {form} on {filed}. Agent 3 reads new 10-K / 10-Q filings on Sunday."
            elif form == "8-K":
                codes = [x.strip() for x in (items or "").split(",") if x.strip() and x.strip() != "9.01"]
                if not codes:
                    continue
                said = "; ".join(f"{EIGHT_K.get(x, 'reported item ' + x)} (item {x})" for x in codes)
                text = f"{s.ticker} filed an 8-K on {filed}: {said}."
            else:
                continue
            url = sec.filing_url(cik, accession, document) if accession and document else None
            kept = [x.strip() for x in (items or "").split(",") if x.strip() and x.strip() != "9.01"] if form == "8-K" else []
            pieces.append(Piece("", "filing", f"{s.ticker} {form}", text, "sec", moment + "Z" if moment else filed, url,
                                tickers=(s.ticker,), data={"form": form, "filed": filed, "items": kept}))
    return [Piece(f"F{n}", p.kind, p.title, p.text, p.site, p.when, p.url, tickers=p.tickers, data=p.data)
            for n, p in enumerate(pieces, 1)], notes


def earnings(stocks: list[StockInfo], today: str, days: int, fetch=None) -> tuple[list[Piece], list[str]]:
    """The next earnings date of each of my stocks that falls in [today, today + days]."""
    fetch = fetch or yahoo.next_earnings
    last = (date.fromisoformat(today) + timedelta(days=days)).isoformat()
    pieces, notes = [], []
    for s in stocks:
        try:
            dates = [d for d in fetch(s.ticker) if today <= d <= last]
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Yahoo has no earnings date for {s.ticker} ({type(exc).__name__})")
            continue
        if dates:
            pieces.append(Piece(f"E{len(pieces) + 1}", "earnings", f"{s.ticker} earnings", f"{s.ticker} reports earnings on {dates[0]} (Yahoo).",
                                "yahoo", dates[0], tickers=(s.ticker,), data={"date": dates[0]}))
    return pieces, notes


# --- web searches -------------------------------------------------------------------------------------------------------

def _queries(stocks: list[StockInfo], c: dict) -> list[tuple[str, str]]:
    """(topic, query) in the order they are spent: stocks I hold, the interest topics, then stocks I only watch."""
    held = [(s.ticker, f"{s.company[:60]} stock news") for s in stocks if s.held]
    interests = [(i["topic"], i["query"]) for i in c["interests"]]
    watched = [(s.ticker, f"{s.company[:60]} stock news") for s in stocks if not s.held]
    return (held + interests + watched)[: int(c["max_searches"])]


def web(stocks: list[StockInfo], since: str, c: dict | None = None, search_fn=None, conn=None, run=None) -> tuple[list[Piece], list[str], int]:
    """Returns (pieces, notes, searches made). Hits older than the window's day before are dropped; one URL appears once."""
    c = c or cfg()
    search_fn = search_fn or search.search
    after = (clock.parse_utc(since).date() - timedelta(days=1)).isoformat()
    pieces, notes, seen, made = [], [], set(), 0
    tickers = {s.ticker for s in stocks}
    for topic, query in _queries(stocks, c):
        try:
            hits = search_fn(query, count=int(c["search_count"]), after=after, conn=conn, run=run)
        except search.SearchError as exc:
            notes.append(f"Web search '{topic}' failed: {exc}")
            if any(x in str(exc) for x in STOP_ON):
                notes.append("The remaining web searches were skipped.")
                break
            continue
        made += 1
        for h in hits:
            if h.url in seen or (h.date and h.date[:10] < after):
                continue
            seen.add(h.url)
            site = h.site_name or urlparse(h.url).netloc
            pieces.append(Piece(f"W{len(pieces) + 1}", "web", h.title, "\n".join(x for x in (h.title, h.summary or h.snippet) if x),
                                site, h.date, h.url, topic=topic, tickers=(topic,) if topic in tickers else ()))
    return pieces, notes, made


# --- everything ---------------------------------------------------------------------------------------------------------

def gather(conn, now: datetime | None = None, *, since: datetime | None = None, search_fn=None, submissions=None,
           earnings_fn=None, searches: bool = True, run=None) -> Pack:
    c = cfg()
    now = now or clock.now_utc()
    start = clock.utc_iso(since or window_start(now))
    pack = Pack(window_start=start, window_end=clock.utc_iso(now))
    pack.stocks = my_stocks(conn)
    mine = {s.ticker for s in pack.stocks}
    pack.posts = posts(conn, start, mine, c)
    ciks = {t: cik for t, cik in conn.execute("SELECT ticker, cik FROM stocks") if cik}
    pack.filings, notes = filings(pack.stocks, ciks, start, submissions)
    pack.notes += notes
    pack.earnings, notes = earnings(pack.stocks, clock.today_local(now), int(c["earnings_days"]), earnings_fn)
    pack.notes += notes
    if searches:
        pack.web, notes, pack.searches = web(pack.stocks, start, c, search_fn, conn, run)
        pack.notes += notes
    return pack


def describe(pack: Pack) -> str:
    """For people: what was gathered (the `--gather` check on the Air). Not the bulletin."""
    lines = [f"GATHERED · window {clock.show(pack.window_start)} → {clock.show(pack.window_end)} (Turkey time)",
             f"my stocks {len(pack.stocks)} · posts {len(pack.posts)} · web hits {len(pack.web)} ({pack.searches} searches) · "
             f"filings {len(pack.filings)} · earnings dates {len(pack.earnings)}"]
    for s in pack.stocks:
        lines.append(f"  {s.ticker}{' (held)' if s.held else ''}: thesis {s.thesis_date or 'none yet'}, {len(s.breaks)} breaks")
    for label, pieces in (("posts", pack.posts[:8]), ("web", pack.web[:8]), ("filings", pack.filings), ("earnings", pack.earnings)):
        if pieces:
            lines.append(f"{label}:")
            lines += [f"  {p.id} · {p.site} · {(p.when or '')[:10]} · {p.title[:90]}" + (f" [{', '.join(p.tickers)}]" if p.tickers else "")
                      for p in pieces]
    lines += [f"note: {n}" for n in pack.notes]
    return "\n".join(lines)
