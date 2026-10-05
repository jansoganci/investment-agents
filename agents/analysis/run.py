"""Agent 3 end to end: SEC → measures → card.md + the database.

    analyze(conn, "KO")   one stock now (by hand, `/analyze`, or the weekly check)
    weekly(conn)          every watching stock: is there a new filing? if so, analyze it; archived stocks never

Sources are passed in (`LiveSources` by default: SEC + Yahoo); tests pass saved sample data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agents.analysis import card
from agents.analysis.measures import Market, Result, analyse
from shared import clock, drive, notify, prices, sec
from shared.prices import yahoo
from shared.sec import FORMS
from shared.sec.facts import Facts

US_STATES = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND "
                "OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR".split())


class Refused(Exception):
    """Analysis does not run; the message says why. Nothing changes."""


class LiveSources:
    def lookup(self, ticker):
        return sec.lookup(ticker)

    def facts(self, cik):
        return sec.company_facts(cik)

    def submissions(self, cik):
        return sec.submissions(cik)

    def chart(self, symbol, range_, interval):
        return yahoo.chart(symbol, range_, interval)

    def market_value(self, symbol):
        return yahoo.market_values([symbol]).get(symbol)


@dataclass
class Outcome:
    stock_id: int
    ticker: str
    grade: str
    text: str
    card_path: str


def find_stock(conn, ticker: str) -> dict | None:
    cur = conn.execute("SELECT * FROM stocks WHERE upper(ticker) = ? ORDER BY id LIMIT 1", (ticker.upper(),))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def _country(subs: dict) -> str | None:
    addr = ((subs.get("addresses") or {}).get("business") or {})
    code = addr.get("stateOrCountry")
    if code in US_STATES:
        return "US"
    desc = addr.get("stateOrCountryDescription")
    return desc.title() if desc else code


def _user_values(conn, stock_id: int) -> dict:
    rows = conn.execute("SELECT figure, period_end, period_type, value FROM financials WHERE stock_id = ? AND "
                        "source = 'user' AND void = 0 ORDER BY id", (stock_id,)).fetchall()
    return {(fig, end): val for fig, end, _pt, val in rows}  # period_end holds the year label for user rows


def _market(conn, ticker: str, currency: str, src) -> tuple[Market, list[str]]:
    notes = []
    try:
        prices.ensure_history(conn, ticker, src)
        split_list = prices.splits(conn, ticker)
    except yahoo.YahooError as exc:
        split_list = None
        notes.append(f"Yahoo did not answer for {ticker} ({exc}); splits cannot be confirmed")
    last = prices.latest_close(conn, ticker)
    fx = 1.0
    fx_sym = prices.fx_symbol(currency)
    if fx_sym:
        try:
            prices.ensure_history(conn, fx_sym, src)
            got = prices.latest_close(conn, fx_sym)
            fx = got[1] if got else None
        except yahoo.YahooError:
            fx = None
    try:
        mv = src.market_value(ticker)
    except yahoo.YahooError:
        mv = None
    return Market(splits=split_list, market_value=mv, price=last[1] if last else None, fx=fx,
                  as_of=last[0] if last else None), notes


def _source(facts: Facts, r: Result, cik: str) -> dict:
    end = r.last or (facts.annual_ends[-1] if facts.annual_ends else None)
    accn, form = None, None
    for fig in ("revenue", "net", "op_cash", "assets"):
        v = facts.annual(fig).get(end) if end else None
        if v is not None and v.accn:
            accn, form = v.accn, v.form
            break
    if end and end == facts.ttm_end:
        label = f"last 4 quarters to {end} ({form or '10-Q'})"
    else:
        label = f"{end[:4] if end else '?'} annual ({form or '10-K'})"
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/" if accn else None
    return {"report": form, "period_end": end, "url": url, "as_of": clock.today_local(), "filing": accn, "label": label}


def _save_financials(conn, stock_id: int, facts: Facts, r: Result, now: str) -> int:
    series = dict(r.figures)
    series["liquid"], series["debt"] = r.liquid, r.debt
    new = 0
    for figure, values in series.items():
        for end, v in values.items():
            if v.form == "user":
                continue
            ptype = "ttm" if end == facts.ttm_end else "annual"
            unit = "shares" if figure == "shares" else (f"{facts.currency}/share" if figure == "eps" else facts.currency)
            exists = conn.execute(
                "SELECT 1 FROM financials WHERE stock_id=? AND period_end=? AND period_type=? AND figure=? AND value=? "
                "AND coalesce(xbrl,'')=? AND source='sec' AND void=0", (stock_id, end, ptype, figure, v.value, v.tag or "")
            ).fetchone()
            if exists:
                continue
            conn.execute("INSERT INTO financials (stock_id, period_end, period_type, form, figure, value, unit, xbrl, "
                         "filing, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'sec', ?)",
                         (stock_id, end, ptype, v.form, figure, v.value, unit, v.tag, v.accn, now))
            new += 1
    return new


def _save_missing(conn, stock_id: int, missing: list[dict], now: str) -> int:
    new = 0
    for m in missing:
        if conn.execute("SELECT 1 FROM missing_data WHERE stock_id=? AND year=? AND figure=? AND status='open'",
                        (stock_id, m["year"], m["figure"])).fetchone():
            continue
        conn.execute("INSERT INTO missing_data (stock_id, year, figure, names_tried, status, created_at) "
                     "VALUES (?, ?, ?, ?, 'open', ?)", (stock_id, m["year"], m["figure"], json.dumps(m["names_tried"]), now))
        new += 1
    return new


def analyze(conn, ticker: str, sources=None, today: str | None = None, raw_facts: dict | None = None) -> Outcome:
    src = sources or LiveSources()
    day = today or clock.today_local()
    now = clock.utc_iso()
    ticker = ticker.upper()
    stock = find_stock(conn, ticker)
    if stock and stock["status"] == "archived":
        raise Refused(f"{ticker} is archived: archived stocks are never analyzed (/unarchive {ticker} first).")
    cik = stock["cik"] if stock and stock.get("cik") else None
    if cik is None:
        found = src.lookup(ticker)
        if not found:
            raise Refused(f"SEC does not know the ticker {ticker} (version 1 is US markets only).")
        cik = found["cik"]
    subs = src.submissions(cik)
    user_values = _user_values(conn, stock["id"]) if stock else {}
    facts = Facts(raw_facts or src.facts(cik), subs, user_values=user_values)
    market, market_notes = _market(conn, ticker, facts.currency, src)
    r = analyse(facts, ticker, market)
    r.notes.extend(market_notes)

    company = (subs.get("name") or facts.name or ticker).title()
    if stock is None:
        cur = conn.execute(
            "INSERT INTO stocks (cik, ticker, company, exchange, country, sector, status, in_portfolio, added_by, "
            "opened, created_at) VALUES (?, ?, ?, ?, ?, ?, 'candidate', 'no', 'user', ?, ?)",
            (cik, ticker, company, (subs.get("exchanges") or [None])[0], _country(subs), r.sector, day, now))
        stock = find_stock(conn, ticker)
        assert stock and stock["id"] == cur.lastrowid
    sid = stock["id"]
    previous = conn.execute("SELECT grade, lynch_type FROM card_entries WHERE stock_id=? AND record='fundamental' "
                            "ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
    previous = {"grade": previous[0], "lynch_type": previous[1]} if previous else None

    path = drive.find_card(ticker) or drive.card_path(ticker, stock["company"] or company)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        head = dict(stock)
        head.update({"company": stock["company"] or company, "sector": stock["sector"] or r.sector,
                     "opened": stock["opened"] or day, "in_portfolio": stock["in_portfolio"]})
        path.write_text(card.new_card(head), encoding="utf-8")
    source = _source(facts, r, cik)
    entry = card.fundamental_entry(r, source, day, previous)
    card.append(path, entry, {"lynch_type": r.lynch_type or "", "grade": r.grade, "last_entry": day})

    conn.execute("UPDATE stocks SET cik=?, lynch_type=?, grade=?, last_entry=?, out_of_scope=?, "
                 "opened=coalesce(opened, ?), sector=coalesce(sector, ?), country=coalesce(country, ?), "
                 "exchange=coalesce(exchange, ?) WHERE id=?",
                 (cik, r.lynch_type, r.grade, day, r.out_of_scope, day, r.sector, _country(subs),
                  (subs.get("exchanges") or [None])[0], sid))
    conn.execute("INSERT INTO card_entries (stock_id, date, record, who, source, grade, lynch_type, filing, created_at) "
                 "VALUES (?, ?, 'fundamental', 'agent_3', ?, ?, ?, ?, ?)",
                 (sid, day, source["label"], r.grade, r.lynch_type, facts.latest_accn, now))
    _save_financials(conn, sid, facts, r, now)
    n_missing = _save_missing(conn, sid, r.missing, now)
    conn.commit()

    lines = [f"Grade {r.grade} · " + (f"out of scope: {r.out_of_scope}" if r.out_of_scope else (r.lynch_type or "type unclear"))
             + f" · {source['label']}"]
    dec = [f"{n} {m['mark'] or 'not_computed'}" for n, m in r.measures.items() if m["decisive"]]
    if dec:
        lines.append("Decisive: " + ", ".join(dec))
    if r.flags:
        lines.append("Flags: " + "; ".join(f"{f['flag']} ({f['detail']})" for f in r.flags))
    if previous and previous["grade"] != r.grade:
        lines.append(f"Grade changed: {previous['grade']} → {r.grade}")
    if n_missing:
        lines.append(f"New missing figures: {n_missing} (see /missing)")
    lines.extend(market_notes)
    lines.append(f"Card: {path}")
    return Outcome(sid, ticker, r.grade, notify.message(f"ANALYSIS · {ticker}", lines), str(path))


def latest_filing(subs: dict) -> str | None:
    recent = (subs.get("filings") or {}).get("recent") or {}
    for form, accn in zip(recent.get("form", []), recent.get("accessionNumber", [])):
        if form in FORMS:
            return accn
    return None


def weekly(conn, sources=None, today: str | None = None) -> str | None:
    """Every watching stock: a new 10-K / 10-Q / 20-F since its last entry → analyze. Archived stocks never.
    Returns a message only when something happened (an analysis or an error)."""
    src = sources or LiveSources()
    done, errors = [], []
    watching = conn.execute("SELECT id, ticker, cik FROM stocks WHERE status='watching' ORDER BY ticker").fetchall()
    for sid, ticker, cik in watching:
        try:
            raw = None
            if cik:
                newest = latest_filing(src.submissions(cik))
                last = conn.execute("SELECT filing FROM card_entries WHERE stock_id=? AND record='fundamental' "
                                    "ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
                if last and newest and last[0] == newest:
                    continue
                raw = src.facts(cik)
                if last and Facts(raw).latest_accn == last[0]:
                    continue  # a new filing is listed but its figures are not in SEC's data yet: next week again
            out = analyze(conn, ticker, src, today, raw_facts=raw)
            done.append(out.text)
        except (Refused, sec.SecError) as exc:
            errors.append(f"{ticker}: {exc}")
    if not done and not errors:
        return None
    parts = done + ([notify.message("ANALYSIS · errors", errors)] if errors else [])
    return "\n\n".join(parts)
