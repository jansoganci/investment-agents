"""Small builders for agent 4's tests: stocks, stored prices (with the time they were stored) and a frozen clock."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from agents.analysis import card
from shared import clock, commands, drive


def stock(db, ticker, status="watching", grade="solid", company=None):
    cur = db.execute("INSERT INTO stocks (ticker, company, status, grade, created_at) VALUES (?, ?, ?, ?, ?)",
                     (ticker, company or f"{ticker} Inc", status, grade, "2026-01-01T00:00:00Z"))
    db.commit()
    return cur.lastrowid


def price(db, symbol, day, close, dividend=None, split=None, stored=None):
    """One stored row; `stored` is the UTC day it was stored (default: the night after `day`)."""
    stored = stored or (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    db.execute("INSERT INTO prices (symbol, date, close, adj_close, currency, source, dividend, split_ratio, created_at) "
               "VALUES (?, ?, ?, ?, 'USD', 'test', ?, ?, ?)", (symbol, day, close, close, dividend, split, f"{stored}T00:00:00Z"))
    db.commit()


def prices(db, symbol, rows):
    for r in rows:
        price(db, symbol, *r)


def freeze(monkeypatch, day, hour=12):
    """Turkey time `day` at `hour`."""
    monkeypatch.setattr(clock, "now_utc", lambda: datetime.fromisoformat(f"{day}T{hour:02d}:00:00+03:00").astimezone(timezone.utc))


def do(*argv):
    return commands.run([*argv, "--yes"])


def fridays(start, n):
    d = date.fromisoformat(start)
    return [(d + timedelta(days=7 * i)).isoformat() for i in range(n)]


def make_card(ticker, company, entries=""):
    path = drive.card_path(ticker, company)
    path.parent.mkdir(parents=True, exist_ok=True)
    card.write(path, card.new_card({"ticker": ticker, "company": company, "status": "watching", "in_portfolio": "no",
                                    "grade": "solid"}) + entries)
    return path


def fundamental(day, price, peg=None, fcf_yield=None):
    return (f"\n## {day} · fundamental · agent_3 · 2025 annual (10-K)\n### Summary\nTest.\n```yaml\n"
            f"price:\n  price: {price}\n  peg: {'null' if peg is None else peg}\n"
            f"  fcf_yield: {'null' if fcf_yield is None else fcf_yield}\n```\n")
