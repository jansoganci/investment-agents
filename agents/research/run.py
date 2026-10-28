"""Agent 2 end to end (roadmap, "Agent 2 rules" 1–8): one stock, then the weekly run.

For each stock: SEC's figures (quick health), the posts (tone), the news (web search), the price trend (sector tailwind). Code adds the
points. The stock, its score, its news events and its card are saved together at the end, inside the write lock, the card last."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta

from agents.analysis import card
from agents.analysis.measures import Market, analyse
from agents.analysis.run import LiveSources
from agents.research import health as health_mod
from agents.research import news as news_mod
from agents.research import page, reading, score, tailwind
from shared import clock, config, drive, notify
from shared import prices as prices_mod
from shared.sectors import GICS
from shared.sec.facts import Facts

STORY_PLACEHOLDER = "> Story: (not written yet — 2 sentences: what it sells, where the money comes from)"
WINDOW_DAYS = 7
STALE_COUNTER_DAYS = 3


class Refused(Exception):
    """A stock that cannot be researched; the message says why."""


@dataclass
class Outcome:
    ticker: str
    company: str
    total: int
    points: dict
    reasons: dict
    added_by: str
    notes: list = field(default_factory=list)
    card_path: str | None = None
    events: list = field(default_factory=list)

    def lines(self) -> list[str]:
        p = self.points
        out = [f"{self.ticker} {self.company} — {self.total}/10 (mentions {p['mentions']} · tone {p['tone']} · tailwind "
               f"{p['sector_tailwind']} · news {p['news_flow']} · health {p['quick_health']})"
               + (" · added by me" if self.added_by == "user" else "")]
        for name in score.CRITERIA:
            out.append(f"   {name}: {self.reasons[name][:220]}")
        return out


def week_label(day: str) -> str:
    year, week, _ = date.fromisoformat(day).isocalendar()
    return f"{year}-W{week:02d}"


def _pretty(name: str) -> str:
    return name.title() if name.isupper() else name


def mentions_points(posts: int) -> int:
    """The same bars as the Counter's (`settings.yaml` `counter.mention_points`): 1–2 posts → 0, 3–5 → 1, 6+ → 2."""
    low, high = (config.settings().get("counter") or {}).get("mention_points", [3, 6])
    return 2 if posts >= high else 1 if posts >= low else 0


def _stock_row(conn, ticker: str) -> dict | None:
    cur = conn.execute("SELECT * FROM stocks WHERE upper(ticker) = ? ORDER BY id LIMIT 1", (ticker.upper(),))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def _tag_facts(conn, ticker: str) -> tuple[str | None, str | None]:
    row = conn.execute("SELECT sector, country FROM tags WHERE kind = 'company' AND upper(maps_to) = ? "
                       "ORDER BY (sector IS NULL), id LIMIT 1", (ticker.upper(),)).fetchone()
    return (row[0], row[1]) if row else (None, None)


def _ensure_prices(conn, symbols: list[str], source=None) -> list[str]:
    notes = []
    for symbol in symbols:
        try:
            prices_mod.ensure_history(conn, symbol, source)
        except Exception as error:  # noqa: BLE001 — Yahoo or the network; the trend is then judged on what is stored
            notes.append(f"prices of {symbol} could not be fetched ({error})")
    return notes


def research_entry(day: str, week: str, o: Outcome, n_posts: int, tone: reading.Tone, tw: tailwind.Tailwind,
                   hl: health_mod.Health, nw: news_mod.News) -> str:
    data = {
        "week": week, "added_by": o.added_by, "score": o.total,
        "criteria": {
            "mentions": {"points": o.points["mentions"], "posts_7d": n_posts, "reason": o.reasons["mentions"]},
            "tone": {"points": tone.points, "positive": tone.positive, "negative": tone.negative, "neutral": tone.neutral,
                     "unreadable": tone.unreadable, "reason": tone.reason, "quotes": tone.examples},
            "sector_tailwind": {"points": tw.points, "sector": tw.detail.get("sector"), "fund": tw.detail.get("fund"),
                                "reason": tw.reason},
            "news_flow": {"points": nw.points, "reason": nw.reason},
            "quick_health": {"points": hl.points, "reason": hl.reason, "checks": hl.checks},
        },
        "events": [{"summary": e.summary, "date": e.date, "class": e.klass, "scope": e.scope, "status": e.status,
                    "source": e.source_url, "note": e.note} for e in nw.events],
        "commodity_links": nw.links,
        "gaps": o.notes,
    }
    summary = [f"Score {o.total}/10." ] + [f"- {name} {o.points[name]}/2 — {o.reasons[name]}" for name in score.CRITERIA]
    return (f"## {day} · research · agent_2\n" + card._block(data) + "### Summary\n" + "\n".join(summary)
            + "\n### What changed\nFirst research entry.\n")


def research_one(conn, ticker: str, *, added_by: str = "counter", sources=None, today: str | None = None, run=None,
                 price_source=None, fetch=None, ensure=None) -> Outcome:
    ticker = ticker.upper()
    sources = sources or LiveSources()
    ensure = ensure or _ensure_prices
    fetch = fetch or page.fetch_text
    day = today or clock.today_local()
    week = week_label(day)
    now = clock.now_utc()
    since = clock.utc_iso(now - timedelta(days=WINDOW_DAYS))

    existing = _stock_row(conn, ticker)
    if drive.find_card(ticker) is not None:
        raise Refused(f"{ticker} already has a card; agent 2 opens cards, it does not score a stock twice")
    if existing is None:
        found = sources.lookup(ticker)
        if not found:
            raise Refused(f"SEC does not know the ticker {ticker}")
    else:
        found = {"cik": existing["cik"], "name": existing["company"] or ticker, "exchange": existing["exchange"]}
        if not found["cik"]:
            found = sources.lookup(ticker) or found
    company = (existing or {}).get("company") or _pretty(found["name"])
    notes: list[str] = []

    # quick health (SEC) and the sector
    sector_sic = None
    try:
        facts = Facts(sources.facts(found["cik"]), sources.submissions(found["cik"]), quarters=False)
        result = analyse(facts, ticker, Market())
        hl = health_mod.quick_health(result)
        sector_sic = result.sector
    except Exception as error:  # noqa: BLE001 — SEC trouble must not stop the week: the check is then unclear
        hl = health_mod.Health([health_mod._check(n, "unclear", "SEC data could not be read") for n in health_mod.CHECKS], 1,
                               f"unclear — SEC data could not be read ({type(error).__name__}: {error})")
        notes.append(hl.reason)
    tag_sector, country = _tag_facts(conn, ticker)
    sector = tag_sector if tag_sector in GICS else (sector_sic if sector_sic in GICS else None)

    posts = reading.posts_of(conn, ticker, since)
    mention_pts = mentions_points(len(posts))
    mention_reason = (f"{len(posts)} distinct post(s) in the last {WINDOW_DAYS} days" if posts
                      else "no post mentions it (a stock added by me, or its tags are not confirmed)")
    tone = reading.tone_for(conn, ticker, company, since, run=run)
    if not posts:
        tone.reason = "no post mentions it in the last 7 days; neutral 1 point"
    notes += tone.notes

    nw = news_mod.search(conn, run, ticker, company, today=date.fromisoformat(day), fetch=fetch)
    if nw.error:
        notes.append(f"news: {nw.error}")
    links = [(l["commodity"], l["role"]) for l in nw.links]
    notes += ensure(conn, tailwind.symbols_needed(sector, links), price_source)
    tw = tailwind.evaluate(conn, sector, links)

    points = {"mentions": mention_pts, "tone": tone.points, "sector_tailwind": tw.points, "news_flow": nw.points,
              "quick_health": hl.points}
    reasons = {"mentions": mention_reason, "tone": tone.reason, "sector_tailwind": tw.reason, "news_flow": nw.reason,
               "quick_health": hl.reason}
    outcome = Outcome(ticker, company, score.total(points), points, reasons, added_by, notes, events=nw.events)

    # one transaction: the stock, its links, its score, its events, then the card file last
    conn.execute("BEGIN IMMEDIATE")
    try:
        if existing is None:
            cur = conn.execute(
                "INSERT INTO stocks (cik, ticker, company, exchange, country, sector, status, in_portfolio, added_by, opened, last_entry,"
                " created_at) VALUES (?, ?, ?, ?, ?, ?, 'candidate', 'no', ?, ?, ?, ?)",
                (found["cik"], ticker, company, found.get("exchange"), country, sector, added_by, day, day, clock.utc_iso()))
            sid = cur.lastrowid
        else:
            sid = existing["id"]
            conn.execute("UPDATE stocks SET sector = COALESCE(sector, ?), country = COALESCE(country, ?), opened = COALESCE(opened, ?),"
                         " last_entry = ? WHERE id = ?", (sector, country, day, day, sid))
        for link in nw.links:
            conn.execute("INSERT OR IGNORE INTO commodity_links (stock_id, commodity, role, source, created_at) VALUES (?, ?, ?, ?, ?)",
                         (sid, link["commodity"], link["role"], link["source"], clock.utc_iso()))
        conn.execute("UPDATE stocks SET commodity_checked = ? WHERE id = ?", (day, sid))
        conn.execute(
            "INSERT OR REPLACE INTO scores (stock_id, week, mentions, tone, sector_tailwind, news_flow, quick_health, score, reasons,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sid, week, points["mentions"], points["tone"], points["sector_tailwind"], points["news_flow"], points["quick_health"],
             outcome.total, json.dumps(reasons, ensure_ascii=False), clock.utc_iso()))
        news_mod.save_events(conn, ticker, week, nw.events)
        conn.execute("INSERT INTO card_entries (stock_id, date, record, who, source, created_at) VALUES (?, ?, 'research', 'agent_2', ?, ?)",
                     (sid, day, f"research {week}", clock.utc_iso()))
        cur = conn.execute("SELECT * FROM stocks WHERE id = ?", (sid,))
        stock = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        path = drive.card_path(ticker, company)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = card.new_card(stock)
        if nw.story:
            text = text.replace(STORY_PLACEHOLDER, f"> Story: {nw.story}")
        card.write(path, text)
        card.append(path, research_entry(day, week, outcome, len(posts), tone, tw, hl, nw), {"last_entry": day})
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    outcome.card_path = str(path)
    return outcome


# --- the weekly run ----------------------------------------------------------------------------------------------------------

def report_text(day: str, outcomes: list[Outcome], errors: list[str], notes: list[str]) -> str:
    lines = [f"# Research · {day}", ""]
    if not outcomes:
        lines.append("No stock was researched this week.")
    for i, o in enumerate(sorted(outcomes, key=lambda o: (-o.total, o.ticker)), 1):
        lines.append(f"## {i}. {o.ticker} {o.company} — {o.total}/10" + (" (added by me)" if o.added_by == "user" else ""))
        lines += [f"- **{name}** {o.points[name]}/2 — {o.reasons[name]}" for name in score.CRITERIA]
        unconfirmed = [e for e in o.events if e.status == "not_confirmed"]
        lines += [f"- not confirmed ({e.klass}): {e.summary} — {e.note}" for e in unconfirmed]
        lines += [f"- note: {n}" for n in o.notes]
        lines.append(f"- card: {o.card_path}")
        lines.append("")
    if errors:
        lines += ["## Not researched", ""] + [f"- {e}" for e in errors] + [""]
    lines += [f"_{n}_" for n in notes]
    return "\n".join(lines).rstrip() + "\n"


def weekly(conn, sources=None, today: str | None = None, run=None, *, limit: int | None = None, fetch=None,
           ensure=None, price_source=None) -> str:
    day = today or clock.today_local()
    last = conn.execute("SELECT max(run_at) FROM counts").fetchone()[0]
    if last is None:
        return notify.message("RESEARCH", ["Nothing to do: the Counter has not run yet (python -m agents.counter)."])
    top = limit or int((config.settings().get("counter") or {}).get("top", 10))
    rows = conn.execute("SELECT key, label FROM counts WHERE run_at = ? AND kind = 'stock' AND has_card = 0 AND rank IS NOT NULL "
                        "AND rank <= ? ORDER BY rank", (last, top)).fetchall()
    notes = []
    age = (date.fromisoformat(day) - date.fromisoformat(clock.today_local(clock.parse_utc(last)))).days  # both in Turkey time
    if age > STALE_COUNTER_DAYS:
        notes.append(f"The latest Counter run is {age} days old ({clock.show(last)}).")
    outcomes, errors = [], []
    for ticker, label in rows:
        try:
            outcomes.append(research_one(conn, ticker, added_by="counter", sources=sources, today=day, run=run, fetch=fetch,
                                         ensure=ensure, price_source=price_source))
        except Refused as error:
            errors.append(f"{ticker}: {error}")
        except Exception as error:  # noqa: BLE001 — one stock must not stop the others
            errors.append(f"{ticker}: {type(error).__name__}: {error}")
    path = drive.weekly() / f"{day}-research.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report_text(day, outcomes, errors, notes), encoding="utf-8")
    lines = []
    for o in sorted(outcomes, key=lambda o: (-o.total, o.ticker)):
        lines += o.lines()
    unconfirmed = sum(1 for o in outcomes for e in o.events if e.status == "not_confirmed")
    if unconfirmed:
        lines.append(f"{unconfirmed} reported event(s) could not be confirmed and are not counted (see the report).")
    lines += [f"Not researched — {e}" for e in errors] + notes
    if not rows:
        lines.append("The Counter's list has no US stock without a card this week.")
    lines.append(f"Report: {path}")
    return notify.message(f"RESEARCH · {len(outcomes)} stock(s) scored (week {week_label(day)})", lines)
