"""Phase 1 commands (roadmap section 10.2): stock state, agent 3's numbers and missing figures.

    /watch KO       candidate → watching (a stock SEC knows but we do not yet: added, "added by me")
    /archive KO     watching or candidate → archived: no new analysis or spend
    /unarchive KO   archived → watching
    /analyze KO     agent 3 now: the numbers + the AI parts, with the estimated cost first (`/analyze KO opus-5.5`: one-off model)
    /card KO · /green · /missing      information
    /data NKE 2026 interest 0.25bn    a missing figure I enter (source: user), with a plausibility check

A state change writes a dated note on the card (if the card exists) and updates its header. /undo puts the previous state
back with another dated note; nothing is deleted.
"""

from __future__ import annotations

import json
import re
import sqlite3
from statistics import median

from shared import clock, drive
from shared.commands import UNDO, Applied, Command, Plan, Refused, register
from shared.sec.synonyms import SYNONYMS

SOURCES = None  # SEC + Yahoo by default (agents.analysis.run.LiveSources); tests put saved data here
FIGURES = sorted(set(SYNONYMS["us-gaap"]) | {"debt"})


def _sources():
    if SOURCES is not None:
        return SOURCES
    from agents.analysis.run import LiveSources

    return LiveSources()


def _stock(conn, ticker: str) -> dict | None:
    cur = conn.execute("SELECT * FROM stocks WHERE upper(ticker)=? ORDER BY id LIMIT 1", (ticker.upper(),))
    row = cur.fetchone()
    return dict(zip([d[0] for d in cur.description], row)) if row else None


def _ticker(args: list[str], usage: str) -> str:
    if len(args) < 1 or not re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", args[0]):
        raise Refused(f"usage: {usage}")
    return args[0].upper()


def _card_note(ticker: str, text: str, header: dict) -> None:
    from agents.analysis import card

    path = drive.find_card(ticker)
    if path is not None:
        card.append(path, card.note_entry(clock.today_local(), text), header)


# --- stock state -----------------------------------------------------------------------------------------------------

def _state_change(name: str, ticker: str, stock: dict | None, new: str, found: dict | None = None) -> Plan:
    """`found`: SEC's answer for a ticker new to us (a new stock, or a renamed ticker of a stock we have)."""
    rename_from = (found or {}).get("rename_from")
    if rename_from:
        stock = rename_from
    old = stock["status"] if stock else None
    label = f"{ticker}" + (f" ({stock['company']})" if stock and stock.get("company") else "")
    if rename_from:
        preview = [f"ticker {rename_from['ticker']} → {ticker} (the same company, SEC CIK {rename_from['cik']}); the card is kept",
                   f"status {old} → {new}" if old != new else f"status stays {old}"]
    elif stock is None:
        preview = [f"{label}: new stock (SEC: {found['name']}), status → {new}", "the card is opened by the first analysis"]
    else:
        preview = [f"{label}: status {old} → {new}", "a dated note on the card"]

    def recheck(conn: sqlite3.Connection) -> None:  # inside the write lock, database only
        now = _stock(conn, ticker)
        if rename_from:
            row = conn.execute("SELECT ticker, status FROM stocks WHERE id=?", (rename_from["id"],)).fetchone()
            if row is None or row[0] != rename_from["ticker"] or row[1] != old:
                raise Refused(f"{rename_from['ticker']} changed meanwhile; send /{name} {ticker} again.")
        elif stock is None and (now or conn.execute("SELECT 1 FROM stocks WHERE cik=?", (found["cik"],)).fetchone()):
            raise Refused(f"{ticker} was added meanwhile; send /{name} {ticker} again.")
        elif stock is not None and (now is None or now["status"] != old):
            raise Refused(f"{ticker}'s status changed meanwhile; send /{name} {ticker} again.")

    def apply(conn: sqlite3.Connection, number: int) -> Applied:
        before = {"status": old, "after": new}
        if rename_from:
            from agents.analysis.run import apply_rename

            apply_rename(conn, ticker, found, clock.today_local())
            before["ticker"] = rename_from["ticker"]
        if stock is None:
            cur = conn.execute("INSERT INTO stocks (cik, ticker, company, status, in_portfolio, added_by, created_at) "
                               "VALUES (?, ?, ?, ?, 'no', 'user', ?)",
                               (found["cik"], ticker, found["name"].title(), new, clock.utc_iso()))
            sid = cur.lastrowid
        else:
            sid = stock["id"]
            if old != new:
                conn.execute("UPDATE stocks SET status=? WHERE id=?", (new, sid))
                _card_note(ticker, f"Status: {old} → {new} (/{name}, change #{number})", {"status": new})
        text = (f"{ticker}: ticker {rename_from['ticker']} → {ticker}; " if rename_from else f"{ticker}: ") + \
            f"status {old or 'new'} → {new}."
        return Applied(text, "stocks", sid, before=before)

    return Plan(preview, [name, ticker], apply, recheck=recheck)


def _watch(conn, args):
    ticker = _ticker(args, "/watch KO")
    stock = _stock(conn, ticker)
    if stock is None:
        from agents.analysis.run import Refused as AnalysisRefused
        from agents.analysis.run import identify

        try:
            _, found = identify(conn, ticker, _sources())
        except AnalysisRefused as exc:
            raise Refused(str(exc)) from exc
        if found.get("rename_from") and found["rename_from"]["status"] == "archived":
            raise Refused(f"{ticker} is the new ticker of {found['rename_from']['ticker']}, which is archived; "
                          f"use /unarchive {found['rename_from']['ticker']}.")
        return _state_change("watch", ticker, None, "watching", found=found)
    if stock["status"] == "watching":
        raise Refused(f"{ticker} is already watching.")
    if stock["status"] == "archived":
        raise Refused(f"{ticker} is archived; use /unarchive {ticker}.")
    return _state_change("watch", ticker, stock, "watching")


def _archive(conn, args):
    ticker = _ticker(args, "/archive KO")
    stock = _stock(conn, ticker)
    if stock is None:
        raise Refused(f"{ticker} is not in the system.")
    if stock["status"] == "archived":
        raise Refused(f"{ticker} is already archived.")
    return _state_change("archive", ticker, stock, "archived")


def _unarchive(conn, args):
    ticker = _ticker(args, "/unarchive KO")
    stock = _stock(conn, ticker)
    if stock is None or stock["status"] != "archived":
        raise Refused(f"{ticker} is not archived.")
    return _state_change("unarchive", ticker, stock, "watching")


def _undo_state(conn, log: dict):
    before = log["before"] or {}
    sid = log["target_id"]
    row = conn.execute("SELECT ticker, status FROM stocks WHERE id=?", (sid,)).fetchone()
    if row is None:
        raise Refused(f"Change #{log['id']}: the stock is gone.")
    ticker, now = row
    if before.get("ticker"):
        raise Refused(f"Change #{log['id']} also changed the ticker ({before['ticker']} → {ticker}); a ticker change is "
                      "not undone (the old ticker no longer trades). Use /archive or /watch instead.")
    if now != before.get("after"):
        raise Refused(f"{ticker}'s status changed since change #{log['id']} (now {now}); undo the later change first.")
    back = before.get("status") or "candidate"  # a stock that /watch added goes back to candidate (rows are never deleted)

    def do(conn, undo_id):
        conn.execute("UPDATE stocks SET status=? WHERE id=?", (back, sid))
        _card_note(ticker, f"Change #{log['id']} withdrawn: status back to {back} (/undo, change #{undo_id})", {"status": back})
        return f"{ticker}: status {now} → {back}."

    return [f"{ticker}: status {now} → {back}; a dated note on the card; nothing is deleted"], do


for _name in ("watch", "archive", "unarchive"):
    UNDO[_name] = _undo_state


# --- /analyze ---------------------------------------------------------------------------------------------------------

def _analyze(conn, args):
    from shared import ai

    if len(args) > 2:
        raise Refused("usage: /analyze KO [model]   (e.g. /analyze KO opus-5.5)")
    ticker = _ticker(args, "/analyze KO [model]")
    model = args[1] if len(args) > 1 else None
    if model is not None:
        try:
            ai.chain("strong", conn, model)
        except ai.AIError as exc:
            raise Refused(str(exc)) from exc
    stock = _stock(conn, ticker)
    if stock and stock["status"] == "archived":
        raise Refused(f"{ticker} is archived: archived stocks are never analyzed (/unarchive {ticker} first).")
    est = ai.estimate("strong", 36000, 6000, model, conn)
    cost = (f"estimated cost about ${est:.2f} (the writing model; the auditor adds a few cents)" if est is not None
            else "estimated cost unknown: this model has no price in settings.yaml")
    preview = [f"analyze {ticker} now: SEC figures + the AI parts (why answers with quotes, thesis, audits) → a new dated "
               "entry on its card" + (f" · model {model}" if model else ""), cost]
    if stock is None:  # ask SEC now, in the preview, not after `yes`
        from agents.analysis.run import Refused as AnalysisRefused
        from agents.analysis.run import identify

        try:
            _, found = identify(conn, ticker, _sources())
        except AnalysisRefused as exc:
            raise Refused(str(exc)) from exc
        if found.get("rename_from"):
            preview.insert(0, f"ticker {found['rename_from']['ticker']} → {ticker} (the same company); the card is kept")
        else:
            preview.insert(0, f"{ticker} ({found['name']}) is new: it is added as a candidate")

    def recheck(conn):
        now = _stock(conn, ticker)
        if now and now["status"] == "archived":
            raise Refused(f"{ticker} is archived: archived stocks are never analyzed (/unarchive {ticker} first).")

    def apply(conn, number):
        def after() -> str:
            from agents.analysis import run as analysis
            from shared import db as dbmod
            from shared import notify, runlog

            try:
                with runlog.run("analysis") as r:
                    c = dbmod.connect()
                    try:
                        return analysis.analyze(c, ticker, _sources(), use_ai=True, run=r, model=model, ask_missing=True).text
                    finally:
                        c.close()
            except Exception as exc:  # noqa: BLE001 — the message must reach me
                return notify.error("analysis", f"{type(exc).__name__}: {exc}")

        return Applied(f"Analysis of {ticker} requested.", None, None, undoable=False, after=after)

    return Plan(preview, ["analyze", ticker] + ([model] if model else []), apply, recheck=recheck)


def _undo_analyze(conn, log):
    raise Refused(f"Change #{log['id']} (/analyze) added an analysis entry; card entries are append-only and stay. "
                  "Run /analyze again later for a fresh entry.")


UNDO["analyze"] = _undo_analyze


# --- information -----------------------------------------------------------------------------------------------------

def _last_entry(text: str) -> tuple[str | None, dict]:
    """(the latest fundamental entry's Summary text, its YAML data)."""
    import yaml

    parts = text.split("\n## ")
    for part in reversed(parts):
        if "· fundamental ·" in part.split("\n", 1)[0]:
            data = {}
            if "```yaml\n" in part:
                data = yaml.safe_load(part.split("```yaml\n", 1)[1].split("\n```", 1)[0]) or {}
            summary = part.split("### Summary\n", 1)[1].split("\n###", 1)[0].strip() if "### Summary\n" in part else None
            return summary, data
    return None, {}


def _card(conn, args):
    ticker = _ticker(args, "/card KO")
    stock = _stock(conn, ticker)
    if stock is None:
        raise Refused(f"{ticker} is not in the system.")
    path = drive.find_card(ticker)
    lines = [f"CARD · {ticker} · {stock['company'] or ''}".rstrip(),
             f"Status {stock['status']} · grade {stock['grade'] or '—'} · {stock['lynch_type'] or 'type —'} · "
             f"last entry {stock['last_entry'] or '—'}"]
    if path is None:
        lines.append("No card yet (it opens with the first analysis).")
    else:
        summary, _ = _last_entry(path.read_text(encoding="utf-8"))
        if summary:
            lines.append(summary)
        lines.append(f"Drive: {path}")
    return "\n".join(lines)


def _green(conn, args):
    rows = conn.execute("SELECT ticker, company, lynch_type FROM stocks WHERE status='watching' AND grade='solid' "
                        "ORDER BY ticker").fetchall()
    if not rows:
        return "GREEN LIST\nEmpty (no watched stock is solid yet)."
    lines = ["GREEN LIST (solid; not a buy list)"]
    for ticker, company, lynch_type in rows:
        price = ""
        path = drive.find_card(ticker)
        if path is not None:
            _, data = _last_entry(path.read_text(encoding="utf-8"))
            verdict = (data.get("price") or {}).get("verdict") or {}
            p = data.get("price") or {}
            bits = [f"PEG {p.get('peg')} ({verdict.get('peg')})", f"FCF yield {p.get('fcf_yield')} ({verdict.get('fcf_yield')})"]
            price = " · " + " · ".join(bits)
        lines.append(f"{ticker} · {company or ''} · {lynch_type or 'type —'}{price}")
    return "\n".join(lines)


def _missing(conn, args):
    rows = conn.execute(
        "SELECT s.ticker, m.figure, m.year, m.names_tried FROM missing_data m JOIN stocks s ON s.id = m.stock_id "
        "WHERE m.status='open' AND NOT EXISTS (SELECT 1 FROM financials f WHERE f.stock_id=m.stock_id AND "
        "f.figure=m.figure AND f.period_end=m.year AND f.source='user' AND f.void=0) ORDER BY s.ticker, m.year, m.figure"
    ).fetchall()
    if not rows:
        return "MISSING FIGURES\nNone waiting."
    lines = ["MISSING FIGURES (not found in SEC's data; missing is not zero)"]
    for ticker, figure, year, tried in rows:
        names = ", ".join(json.loads(tried or "[]")[:3])
        lines.append(f"{ticker} · {figure} · {year} — names tried: {names} · answer: /data {ticker} {year} {figure} <value>")
    return "\n".join(lines)


# --- /data -----------------------------------------------------------------------------------------------------------

def _amount(text: str) -> float:
    m = re.fullmatch(r"(-?[0-9][0-9_,]*\.?[0-9]*(?:e[+-]?[0-9]+)?)(bn|b|m|k)?", text.strip().lower())
    if not m:
        raise Refused(f"Not a number: {text!r} (e.g. 0.25bn, 250m, 1200000).")
    value = float(m.group(1).replace(",", "").replace("_", ""))
    return value * {"bn": 1e9, "b": 1e9, "m": 1e6, "k": 1e3, None: 1}[m.group(2)]


def _data(conn, args):
    usage = "/data NKE 2026 interest 0.25bn  (or /data NKE TTM 2026-06-28 interest 0.25bn)"
    if len(args) < 4:
        raise Refused(f"usage: {usage}")
    ticker = _ticker(args, usage)
    if args[1].upper() == "TTM":
        if len(args) != 5:
            raise Refused(f"usage: {usage}")
        year, figure, raw = f"TTM {args[2]}", args[3].lower(), args[4]
    else:
        if len(args) != 4 or not re.fullmatch(r"\d{4}", args[1]):
            raise Refused(f"usage: {usage}")
        year, figure, raw = args[1], args[2].lower(), args[3]
    stock = _stock(conn, ticker)
    if stock is None:
        raise Refused(f"{ticker} is not in the system.")
    if figure not in FIGURES:
        raise Refused(f"Unknown figure {figure!r}. Known: {', '.join(FIGURES)}.")
    value = _amount(raw)
    others = [v for (v,) in conn.execute(
        "SELECT value FROM financials WHERE stock_id=? AND figure=? AND source='sec' AND void=0 AND value IS NOT NULL",
        (stock["id"], figure))]
    preview = [f"{ticker} · {figure} · {year} = {value:,.0f} (source: user; the next analysis uses it where SEC has nothing)"]
    if others:
        mid = median(others)
        if mid and (value == 0 or not 0.1 <= abs(value / mid) <= 10):
            preview.append(f"⚠ far from the other years (median {mid:,.0f}) — are you sure?")

    def apply(conn, number):
        cur = conn.execute(
            "INSERT INTO financials (stock_id, period_end, period_type, figure, value, source, command_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'user', ?, ?)",
            (stock["id"], year, "ttm" if year.startswith("TTM") else "annual", figure, value, number, clock.utc_iso()))
        return Applied(f"{ticker} · {figure} · {year} = {value:,.0f} (source: user).", "financials", cur.lastrowid)

    return Plan(preview, ["data", *args], apply)


register(Command("watch", "Start watching a stock (agent 3 keeps its card)", "/watch KO", changes=True, phase=1,
                 plan=_watch))
register(Command("archive", "Archive a stock: no new analysis or spend", "/archive KO", changes=True, phase=1,
                 plan=_archive))
register(Command("unarchive", "Bring an archived stock back to watching", "/unarchive KO", changes=True, phase=1,
                 plan=_unarchive))
register(Command("analyze", "Run agent 3 now (shows the estimated cost first)", "/analyze KO", changes=True, phase=1,
                 plan=_analyze))
register(Command("card", "Summary of the latest card entry and its Drive link", "/card KO", phase=1, info=_card))
register(Command("green", "The green list: type, grade, price line", "/green", phase=1, info=_green))
register(Command("missing", "Missing figures waiting for me", "/missing", phase=1, info=_missing))
register(Command("data", "Enter a missing figure I was asked for", "/data NKE 2026 interest 0.25bn", changes=True,
                 phase=1, plan=_data))
