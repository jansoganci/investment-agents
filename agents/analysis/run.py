"""Agent 3 end to end: SEC → measures → card.md + the database.

    analyze(conn, "KO")   one stock now (by hand, `/analyze`, or the weekly check)
    weekly(conn)          every watching stock: is there a new filing? if so, analyze it; archived stocks never

Sources are passed in (`LiveSources` by default: SEC + Yahoo); tests pass saved sample data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agents.analysis import ai as ai_parts
from agents.analysis import ask, card
from agents.analysis.measures import Market, Result, analyse
from shared import ai, auditor, clock, drive, notify, prices, sec
from shared.prices import yahoo
from shared.sec import FORMS, filing
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

    def filing_text(self, cik, accession, document):
        return filing.html_to_text(sec.filing_html(cik, accession, document))

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


def identify(conn, ticker: str, src) -> tuple[dict | None, dict | None]:
    """(the stock as we have it, SEC's answer). The identity is the internal number + CIK; the ticker is a label.
    A ticker new to us whose company (CIK) we already have is either another share class of it (refused: the card is under
    the other ticker) or a renamed ticker (FB → META: `found["rename_from"]` holds the stock to relabel)."""
    stock = find_stock(conn, ticker)
    if stock and stock.get("cik"):
        return stock, None
    found = src.lookup(ticker)
    if not found:
        raise Refused(f"SEC does not know the ticker {ticker} (version 1 is US markets only).")
    if stock is None:
        cur = conn.execute("SELECT * FROM stocks WHERE cik = ?", (found["cik"],))
        row = cur.fetchone()
        if row:
            other = dict(zip([d[0] for d in cur.description], row))
            if other["ticker"].upper() in [t.upper() for t in found.get("all_tickers", [])]:
                raise Refused(f"{ticker} is another share class of {other['ticker']} (the same company); "
                              f"its card is under {other['ticker']}.")
            found["rename_from"] = other
    return stock, found


def apply_rename(conn, ticker: str, found: dict, day: str) -> dict:
    """Relabel a stock whose ticker changed: database + card (folder, header, a dated note). Inside the write lock."""
    old = found["rename_from"]
    conn.execute("UPDATE stocks SET ticker = ? WHERE id = ?", (ticker, old["id"]))
    path = drive.find_card(old["ticker"])
    if path is not None:
        card.rename_ticker(path, old["ticker"], ticker, day,
                           f"Ticker: {old['ticker']} → {ticker} (the same company, SEC CIK {old['cik']}).")
    return find_stock(conn, ticker)


def _context(conn, stock, ticker: str, company: str, run, model, rng, news) -> "ai_parts.Context":
    ctx = ai_parts.Context(ticker=ticker, company=company, run=run, model=model, news=news)
    if rng is not None:
        ctx.rng = rng
    if stock:
        ctx.stock_id = stock["id"]
        ctx.in_portfolio = stock["in_portfolio"] == "yes"
        ctx.grades = [g for (g,) in conn.execute("SELECT grade FROM card_entries WHERE stock_id=? AND record='fundamental' "
                                                 "ORDER BY id", (stock["id"],))]
        ctx.first = not ctx.grades
        path = drive.find_card(ticker)
        if path is not None and path.exists():
            body = path.read_text(encoding="utf-8")
            last = card.last_thesis(body)
            if last:
                ctx.previous_thesis_date, ctx.previous_thesis = last
                ctx.notes = card.notes_since(body, last[0])
    return ctx


def _ai_part(conn, stock, ticker, company, cik, subs, source, r, src, run, model, rng, news):
    """The AI parts for this analysis: (the part, its context). Any problem is noted, never raised."""
    accn = source.get("filing")
    doc = sec.primary_document(subs, accn) if accn else None
    ctx = _context(conn, stock, ticker, company, run, model, rng, news)
    ctx.filing = accn
    if not (accn and doc):
        return ai_parts.AIPart(notes=["AI skipped: the filing's main document was not found"]), ctx
    try:
        text = src.filing_text(cik, accn, doc)
    except sec.SecError as exc:
        return ai_parts.AIPart(notes=[f"AI skipped: the filing text could not be fetched ({exc})"]), ctx
    return ai_parts.run_ai(r, text, ctx), ctx


def analyze(conn, ticker: str, sources=None, today: str | None = None, raw_facts: dict | None = None, *,
            use_ai: bool = False, run=None, model: str | None = None, rng=None, news: list | None = None,
            ask_missing: bool = False) -> Outcome:
    src = sources or LiveSources()
    day = today or clock.today_local()
    now = clock.utc_iso()
    ticker = ticker.upper()
    stock, found = identify(conn, ticker, src)
    if stock and stock["status"] == "archived":
        raise Refused(f"{ticker} is archived: archived stocks are never analyzed (/unarchive {ticker} first).")
    cik = stock["cik"] if stock else found["cik"]
    # the slow part (SEC, Yahoo) runs before the write lock
    subs = src.submissions(cik)
    user_values = _user_values(conn, stock["id"]) if stock else {}
    facts = Facts(raw_facts or src.facts(cik), subs, user_values=user_values)
    market, market_notes = _market(conn, ticker, facts.currency, src)
    r = analyse(facts, ticker, market)
    r.notes.extend(market_notes)
    company = (subs.get("name") or facts.name or ticker).title()
    source = _source(facts, r, cik)
    old_path = drive.find_card(ticker)
    r.codes, r.closed = card.assign_codes(
        old_path.read_text(encoding="utf-8") if old_path is not None and old_path.exists() else None, r.flags)
    part, ctx = (None, None)
    if use_ai and not r.out_of_scope:  # the AI calls are slow: they run before the write lock, like SEC and Yahoo
        part, ctx = _ai_part(conn, stock, ticker, company, cik, subs, source, r, src, run, model, rng, news)

    conn.commit()
    conn.execute("BEGIN IMMEDIATE")  # the card and the database change together, one writer at a time
    try:
        if found and found.get("rename_from"):
            stock = apply_rename(conn, ticker, found, day)
        stock = find_stock(conn, ticker)
        if stock and stock["status"] == "archived":
            raise Refused(f"{ticker} is archived: archived stocks are never analyzed (/unarchive {ticker} first).")
        if stock is None:
            conn.execute(
                "INSERT INTO stocks (cik, ticker, company, exchange, country, sector, status, in_portfolio, added_by, "
                "opened, created_at) VALUES (?, ?, ?, ?, ?, ?, 'candidate', 'no', 'user', ?, ?)",
                (cik, ticker, company, (subs.get("exchanges") or [None])[0], _country(subs), r.sector, day, now))
            stock = find_stock(conn, ticker)
        sid = stock["id"]
        previous = conn.execute("SELECT grade, lynch_type FROM card_entries WHERE stock_id=? AND record='fundamental' "
                                "ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
        previous = {"grade": previous[0], "lynch_type": previous[1]} if previous else None
        conn.execute("UPDATE stocks SET cik=?, lynch_type=?, grade=?, last_entry=?, out_of_scope=?, "
                     "opened=coalesce(opened, ?), sector=coalesce(sector, ?), country=coalesce(country, ?), "
                     "exchange=coalesce(exchange, ?) WHERE id=?",
                     (cik, r.lynch_type, r.grade, day, r.out_of_scope, day, r.sector, _country(subs),
                      (subs.get("exchanges") or [None])[0], sid))
        conn.execute("INSERT INTO card_entries (stock_id, date, record, who, source, grade, lynch_type, thesis_status, "
                     "unverified, filing, created_at) VALUES (?, ?, 'fundamental', 'agent_3', ?, ?, ?, ?, ?, ?, ?)",
                     (sid, day, source["label"], r.grade, r.lynch_type, part.thesis_status if part else None,
                      1 if part and part.unverified else 0, facts.latest_accn, now))
        for a in (part.audits if part else []):
            auditor.save(conn, sid, a, facts.latest_accn)
        _save_financials(conn, sid, facts, r, now)
        n_missing = _save_missing(conn, sid, r.missing, now)
        # the card last: if anything above fails, the card is not touched
        path = drive.find_card(ticker) or drive.card_path(ticker, stock["company"] or company)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            head = dict(stock)
            head.update({"company": stock["company"] or company, "sector": stock["sector"] or r.sector,
                         "opened": stock["opened"] or day})
            card.write(path, card.new_card(head))
        card.append(path, card.fundamental_entry(r, source, day, previous, part,
                                                 ctx.previous_thesis_date if ctx else None),
                    {"lynch_type": r.lynch_type or "unclear", "grade": r.grade, "last_entry": day})
        conn.commit()
    except BaseException:
        conn.rollback()
        raise

    lines = [f"Grade {r.grade} · " + (f"out of scope: {r.out_of_scope}" if r.out_of_scope else (r.lynch_type or "type unclear"))
             + f" · {source['label']}"]
    if found and found.get("rename_from"):
        lines.append(f"Ticker changed: {found['rename_from']['ticker']} → {ticker} (same company; card kept)")
    dec = [f"{n} {m['mark'] or 'not_computed'}" for n, m in r.measures.items() if m["decisive"]]
    if dec:
        lines.append("Decisive: " + ", ".join(dec))
    still_open = ai_parts.open_flags(r)
    if still_open:
        lines.append("Flags: " + "; ".join(f"{f['flag']} ({f['detail']})" for _, f in still_open))
    if len(still_open) < len(r.flags):
        lines.append(f"{len(r.flags) - len(still_open)} warning(s) closed by me stay closed.")
    if previous and previous["grade"] != r.grade:
        lines.append(f"Grade changed: {previous['grade']} → {r.grade}")
    if n_missing:
        lines.append(f"New missing figures: {n_missing} (see /missing)")
    lines.extend(market_notes)
    if part is not None:
        lines.extend(part.lines())
    lines.append(f"Card: {path}")
    text = notify.message(f"ANALYSIS · {ticker}", lines)
    if part is not None and part.sell:
        text += "\n\n" + part.sell["text"]
    if ask_missing:
        request = ask.request(conn, ticker, run, plain=use_ai)
        if request:
            text += "\n\n" + request
    return Outcome(sid, ticker, r.grade, text, str(path))


def latest_filing(subs: dict) -> str | None:
    recent = (subs.get("filings") or {}).get("recent") or {}
    for form, accn in zip(recent.get("form", []), recent.get("accessionNumber", [])):
        if form in FORMS:
            return accn
    return None


def weekly(conn, sources=None, today: str | None = None, *, use_ai: bool = False, run=None) -> str | None:
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
            out = analyze(conn, ticker, src, today, raw_facts=raw, use_ai=use_ai, run=run)
            done.append(out.text)
        except Exception as exc:  # noqa: BLE001 — one stock's error must not stop the others
            errors.append(f"{ticker}: {type(exc).__name__}: {exc}")
    request = ask.request(conn, None, run, plain=use_ai)  # the gaps of this run, in one message (a figure is asked once, reminded once)
    if not done and not errors and not request:
        return None
    parts = done + ([notify.message("ANALYSIS · errors", errors)] if errors else []) + ([request] if request else [])
    return "\n\n".join(parts)


def drop_alerts(conn, sources=None, today: str | None = None, *, run=None, news=None) -> str | None:
    """Each pending `drop_alert` signal (agent 4, phase 3): the latest filing (+ the news handed in) against the thesis.
    A dated note goes on the card, the signal becomes `done`. News alone only says `watch` (roadmap, "Agent 3's AI parts")."""
    src = sources or LiveSources()
    day = today or clock.today_local()
    out = []
    rows = conn.execute("SELECT id, stock_id, detail FROM signals WHERE kind='drop_alert' AND status='pending' ORDER BY id").fetchall()
    for sig_id, stock_id, detail in rows:
        cur = conn.execute("SELECT * FROM stocks WHERE id = ?", (stock_id,))
        stock = dict(zip([d[0] for d in cur.description], cur.fetchone()))
        if stock["status"] == "archived":  # an archived stock is never analyzed
            conn.execute("UPDATE signals SET status='done' WHERE id=?", (sig_id,))
            conn.commit()
            continue
        try:
            subs = src.submissions(stock["cik"])
            accn = latest_filing(subs)
            doc = sec.primary_document(subs, accn) if accn else None
            if not doc:
                raise sec.SecError("the latest filing's main document was not found")
            text = src.filing_text(stock["cik"], accn, doc)
            ctx = _context(conn, stock, stock["ticker"], stock["company"] or stock["ticker"], run, None, None,
                           (news or {}).get(stock["ticker"]))
            if ctx.previous_thesis is None:
                out.append(f"DROP ALERT · {stock['ticker']} — no thesis is written yet; run /analyze {stock['ticker']} first.")
                continue
            res = ai_parts.drop_alert_check(type("R", (), {"grade": stock["grade"]})(), text, ctx)
        except (ai.AIError, ai_parts.AIFormatError, sec.SecError) as exc:
            out.append(f"DROP ALERT · {stock['ticker']} — the check could not run ({exc}); the alert stays pending.")
            continue
        note = (f"Drop alert checked against the latest filing ({accn}) — thesis {res['status']}. {res['reason']}"
                + (f' Quote: "{res["quote"]}"' if res["quote"] else "")
                + (" (filing and news)" if res["news_used"] else " (filing only; no news was available)"))
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("INSERT INTO card_entries (stock_id, date, record, who, source, thesis_status, created_at) "
                         "VALUES (?, ?, 'note', 'agent_3', 'drop alert', ?, ?)", (stock_id, day, res["status"], clock.utc_iso()))
            conn.execute("UPDATE signals SET status='done' WHERE id=?", (sig_id,))
            path = drive.find_card(stock["ticker"])
            if path is not None:
                card.append(path, card.note_entry(day, note, who="agent_3"), {"last_entry": day})
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        out.append(f"DROP ALERT · {stock['ticker']} — thesis {res['status']}: {res['reason']}"
                   + (f"\nRun /analyze {stock['ticker']} for a full check." if res["status"] != "intact" else ""))
    return "\n\n".join(out) if out else None
