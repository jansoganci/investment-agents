"""Asking me for a missing figure (roadmap section 3, "Telegram and Hermes", "Asking for missing data").

The message is plain: which stock · which figure · which year · why it is needed · where to find it · how to answer.
Code fills the template; a cheap model may only make it plainer, and code throws its text away if a ticker, a year or a
command is lost. A figure is asked once; if no answer comes, it is reminded once (a week later).
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from shared import ai, clock

HELP = {  # figure: (name, why it is needed, where to find it)
    "revenue": ("Revenue", "the revenue growth and the margins cannot be computed", "income statement → 'Total revenue'"),
    "cost": ("Cost of revenue", "the gross margin cannot be checked", "income statement → 'Cost of revenue'"),
    "gross": ("Gross profit", "the gross margin and the gross-profit growth cannot be computed", "income statement → 'Gross profit'"),
    "operating": ("Operating income", "the operating margin and the capital return cannot be computed", "income statement → 'Income from operations'"),
    "net": ("Net income", "the profit years, cash conversion and the P/E cannot be computed", "income statement → 'Net income'"),
    "interest": ("Interest expense", "the interest cover cannot be computed", "income statement or the debt note → 'Interest expense'"),
    "op_cash": ("Operating cash flow", "cash conversion and free cash cannot be computed", "cash flow statement → 'Net cash provided by operating activities'"),
    "capex": ("Capital spending", "free cash cannot be computed", "cash flow statement → 'Purchases of property and equipment'"),
    "stock_comp": ("Stock-based compensation", "free cash (after stock pay) cannot be computed", "cash flow statement → 'Stock-based compensation'"),
    "dividends": ("Dividends paid", "the dividend cover cannot be computed", "cash flow statement → 'Dividends paid'"),
    "shares": ("Diluted shares", "the share-count measure cannot be computed", "income statement → 'Weighted average shares, diluted'"),
    "eps": ("Diluted EPS", "the PEG cannot be computed", "income statement → 'Diluted earnings per share'"),
    "cash": ("Cash and equivalents", "the liquid assets and the debt measures cannot be computed", "balance sheet → 'Cash and cash equivalents'"),
    "marketable_securities": ("Marketable securities", "the liquid assets may be too low", "balance sheet → 'Marketable securities' (or 'Short-term investments')"),
    "short_term_investments": ("Short-term investments", "the liquid assets may be too low", "balance sheet → 'Short-term investments'"),
    "debt": ("Total debt", "the debt measures cannot be computed", "balance sheet → 'Long-term debt' + its current portion (+ short-term borrowings); the debt note lists them"),
    "assets": ("Total assets", "the capital return cannot be computed", "balance sheet → 'Total assets'"),
    "current_liabilities": ("Current liabilities", "the capital return cannot be computed", "balance sheet → 'Total current liabilities'"),
}


def _help(figure: str) -> tuple[str, str, str]:
    return HELP.get(figure, (figure, "a measure cannot be computed", "the filing's financial statements"))


def template(rows: list[tuple], reminder: bool = False) -> str:
    """rows: [(ticker, year, figure)] → the plain message."""
    lines = [("REMINDER — " if reminder else "") + "MISSING FIGURES — I need your help",
             "SEC's data does not have these figures. A missing figure is never counted as zero."]
    for ticker, year, figure in rows:
        name, why, where = _help(figure)
        cmd_year = year[4:] if year.startswith("TTM ") else year
        lines.append(f"{ticker} · {year} · {name}\n  Why: {why}.\n  Where: {where}.\n"
                     f"  Answer: /data {ticker} {'TTM ' if year.startswith('TTM ') else ''}{cmd_year} {figure} <value, e.g. 0.25bn>")
    return "\n".join(lines)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"/data \S+ \S+ \S+|\b[A-Z]{1,5}\b|\b20\d\d\b", text))


def simplify(text: str, run=None) -> str:
    """The cheap model makes the message plainer; its text is used only if every ticker, year and command is still there."""
    try:
        reply = ai.call("cheap", "Rewrite this message in plainer words for a beginner. Keep every ticker, year, figure name and "
                        "/data command exactly. Keep the same layout. Answer with the message only.\n\n" + text, run=run)
    except ai.AIError:
        return text
    return reply.text.strip() if _tokens(text) <= _tokens(reply.text) else text


def pending(conn, ticker: str | None = None) -> list[dict]:
    q = ("SELECT m.id, s.ticker, m.year, m.figure, m.asked_at, m.reminded_at FROM missing_data m JOIN stocks s ON s.id = m.stock_id "
         "WHERE m.status='open' AND NOT EXISTS (SELECT 1 FROM financials f WHERE f.stock_id=m.stock_id AND f.figure=m.figure "
         "AND f.period_end=m.year AND f.source='user' AND f.void=0)")
    args = []
    if ticker:
        q += " AND upper(s.ticker) = ?"
        args.append(ticker.upper())
    q += " ORDER BY s.ticker, m.year, m.figure"
    cols = ("id", "ticker", "year", "figure", "asked_at", "reminded_at")
    return [dict(zip(cols, r)) for r in conn.execute(q, args).fetchall()]


def request(conn, ticker: str | None = None, run=None, plain: bool = True, today: str | None = None) -> str | None:
    """The message for the figures not asked yet (asked now) and the ones asked a week ago and not answered (reminded once).
    Marks them. None when there is nothing to ask. Call it outside a write transaction."""
    day = today or clock.today_local()
    week_ago = (date.fromisoformat(day) - timedelta(days=7)).isoformat()
    new = [r for r in pending(conn, ticker) if r["asked_at"] is None]
    remind = [r for r in pending(conn, ticker) if r["asked_at"] and r["reminded_at"] is None and r["asked_at"][:10] <= week_ago]
    parts = []
    for rows, is_reminder in ((new, False), (remind, True)):
        if rows:
            text = template([(r["ticker"], r["year"], r["figure"]) for r in rows], reminder=is_reminder)
            parts.append(simplify(text, run) if plain else text)
    if not parts:
        return None
    now = clock.utc_iso()
    for r in new:
        conn.execute("UPDATE missing_data SET asked_at = ? WHERE id = ?", (now, r["id"]))
    for r in remind:
        conn.execute("UPDATE missing_data SET reminded_at = ? WHERE id = ?", (now, r["id"]))
    conn.commit()
    return "\n\n".join(parts)
