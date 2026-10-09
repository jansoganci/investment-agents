"""Phase 3 commands (roadmap section 10.2): my money.

    /bought 10 KO 85.65 [2026-10-08] [fee]   a `buy` row; on the first buy in_portfolio = yes and a card note
    /sold 5 KO 92.10 [2026-10-08] [fee]      a `sell` row; never more than I hold; at 0 in_portfolio = no and a card note
    /gold 1 4689                             grams and the TL price per gram (a sale: minus grams) → `other_assets`
    /bes 8670 245000                         this month's BES payment and the BES total (TL) → `other_assets`
    /portfolio                               the portfolio block (information)

"Are you sure?" checks (roadmap, "AI auditor" table, Hermes commands): a buy or sale price more than 20% from that day's close;
a gold price more than 20% from that day's world gram price in TL; a BES total more than 50% from the last one. The preview shows
the warning; nothing changes until my `yes`. An unknown ticker is refused. `/undo` marks the row `void`, never deletes it.
"""

from __future__ import annotations

import re
import sqlite3

from shared import clock
from shared.commands import UNDO, Applied, Command, Plan, Refused, register
from shared.commands.stocks import _card_note, _stock

PRICE_GAP = 0.20
BES_GAP = 0.50
CLOSE_MAX_GAP_DAYS = 5  # "that day's close": the close of that day, or of the last trading day before it


def _num(text: str, what: str) -> float:
    try:
        x = float(text.replace(",", ""))
    except ValueError:
        raise Refused(f"Not a number for {what}: {text!r}.") from None
    if x != x or x in (float("inf"), float("-inf")):
        raise Refused(f"Not a number for {what}: {text!r}.")
    return x


def _trade_args(name: str, args: list[str]) -> tuple[float, str, float, str, float]:
    usage = f"/{name} 10 KO 85.65 [YYYY-MM-DD] [fee]"
    if not 3 <= len(args) <= 5:
        raise Refused(f"usage: {usage}")
    qty = _num(args[0], "the quantity")
    if not re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", args[1]):
        raise Refused(f"usage: {usage}")
    ticker = args[1].upper()
    price = _num(args[2], "the price")
    day, fee = clock.today_local(), 0.0
    for extra in args[3:]:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", extra):
            day = extra
        else:
            fee = _num(extra, "the fee")
    if qty <= 0 or price <= 0 or fee < 0:
        raise Refused("The quantity and the price must be above 0, the fee 0 or more.")
    try:
        from datetime import date

        date.fromisoformat(day)
    except ValueError:
        raise Refused(f"Not a date: {day} (YYYY-MM-DD).") from None
    if day > clock.today_local():
        raise Refused(f"{day} is in the future.")
    return qty, ticker, price, day, fee


def _price_check(conn, ticker: str, day: str, price: float) -> str:
    from agents.portfolio.marketdata import Series

    series = Series(conn, ticker, day)
    got = series.close_on(day, CLOSE_MAX_GAP_DAYS)
    if got is None:
        return f"no close of {ticker} is stored for {day}: the price is not checked"
    close = got[1] * series.day_factor(got[0])  # in the shares of that day
    gap = price / close - 1
    if abs(gap) > PRICE_GAP:
        return f"⚠ ${price:,.2f} is {gap:+.0%} from {ticker}'s close on {got[0]} (${close:,.2f}) — are you sure?"
    return f"price checked: {gap:+.1%} from {ticker}'s close on {got[0]} (${close:,.2f})"


def _known(conn, ticker: str) -> dict:
    stock = _stock(conn, ticker)
    if stock is None:
        raise Refused(f"{ticker} is not in the system: an unknown ticker is refused (/watch {ticker} first).")
    return stock


def _held(conn, stock_id: int, rows=None, upto=None) -> float:
    from agents.portfolio import ledger

    return ledger.quantity(conn, stock_id, upto, rows)


def _negative(conn, rows) -> list[tuple[str, str, float]]:
    from agents.portfolio import ledger

    return ledger.replay(conn, None, rows).negative


def _set_in_portfolio(conn, stock: dict, number: int, why: str) -> str:
    """in_portfolio from the ledger now; a card note when it changes. Returns a short line or ''."""
    now = "yes" if _held(conn, stock["id"]) > 1e-9 else "no"
    old = conn.execute("SELECT in_portfolio FROM stocks WHERE id=?", (stock["id"],)).fetchone()[0]
    if now == old:
        return ""
    conn.execute("UPDATE stocks SET in_portfolio=? WHERE id=?", (now, stock["id"]))
    _card_note(stock["ticker"], f"In portfolio: {old} → {now} ({why}, change #{number})", {"in_portfolio": now})
    return f" In portfolio: {now}."


def _bought(conn, args):
    qty, ticker, price, day, fee = _trade_args("bought", args)
    stock = _known(conn, ticker)
    total = qty * price + fee
    preview = [f"a buy row: {qty:g} {ticker} at ${price:,.2f} on {day}" + (f" + fee ${fee:,.2f}" if fee else "")
               + f" = ${total:,.2f}",
               _price_check(conn, ticker, day, price)]
    if _held(conn, stock["id"]) <= 1e-9:
        preview.append(f"{ticker} goes into the portfolio (in_portfolio: yes) and a dated note on its card")

    def apply(conn: sqlite3.Connection, number: int) -> Applied:
        cur = conn.execute("INSERT INTO holdings (kind, stock_id, date, quantity, price, fee, command_id, created_at) "
                           "VALUES ('buy', ?, ?, ?, ?, ?, ?, ?)", (stock["id"], day, qty, price, fee, number, clock.utc_iso()))
        extra = _set_in_portfolio(conn, stock, number, "/bought")
        return Applied(f"Buy recorded: {qty:g} {ticker} at ${price:,.2f} on {day} (${total:,.2f}).{extra}", "holdings",
                       cur.lastrowid)

    return Plan(preview, ["bought", *args], apply)


def _sold(conn, args):
    qty, ticker, price, day, fee = _trade_args("sold", args)
    stock = _known(conn, ticker)
    have = _held(conn, stock["id"], upto=day)
    if qty > have + 1e-9:
        raise Refused(f"You hold {have:g} {ticker} on {day}; a sale of {qty:g} is more than that.")
    from agents.portfolio import ledger

    rows = ledger.user_rows(conn) + [{"id": 10**12, "kind": "sell", "stock_id": stock["id"], "ticker": ticker, "date": day,
                                      "quantity": qty, "price": price, "fee": fee}]
    if _negative(conn, rows):
        raise Refused(f"With this sale a later sale of {ticker} would be more than you hold; check the dates.")
    preview = [f"a sale row: {qty:g} {ticker} at ${price:,.2f} on {day}" + (f" − fee ${fee:,.2f}" if fee else "")
               + f" = ${qty * price - fee:,.2f}",
               _price_check(conn, ticker, day, price)]
    left = _held(conn, stock["id"], rows)
    if left <= 1e-9:
        preview.append(f"the {ticker} position reaches 0: in_portfolio: no and a dated note on its card")

    def apply(conn: sqlite3.Connection, number: int) -> Applied:
        cur = conn.execute("INSERT INTO holdings (kind, stock_id, date, quantity, price, fee, command_id, created_at) "
                           "VALUES ('sell', ?, ?, ?, ?, ?, ?, ?)", (stock["id"], day, qty, price, fee, number, clock.utc_iso()))
        extra = _set_in_portfolio(conn, stock, number, "/sold")
        return Applied(f"Sale recorded: {qty:g} {ticker} at ${price:,.2f} on {day}; {left:g} left.{extra}", "holdings",
                       cur.lastrowid)

    return Plan(preview, ["sold", *args], apply)


def _undo_trade(conn, log: dict):
    from agents.portfolio import ledger

    row = conn.execute("SELECT h.stock_id, s.ticker, h.void FROM holdings h JOIN stocks s ON s.id = h.stock_id WHERE h.id=?",
                       (log["target_id"],)).fetchone()
    if row is None or row[2]:
        raise Refused(f"Change #{log['id']}: its ledger row is not there or already void.")
    sid, ticker, _ = row
    rows = [r for r in ledger.user_rows(conn) if r["id"] != log["target_id"]]
    if ledger.replay(conn, None, rows).negative:
        raise Refused(f"Without change #{log['id']} a later sale of {ticker} would be more than you hold; undo that sale first.")
    stock = {"id": sid, "ticker": ticker}

    def do(conn, undo_id):
        conn.execute("UPDATE holdings SET void=1, voided_by=? WHERE id=?", (undo_id, log["target_id"]))
        return _set_in_portfolio(conn, stock, undo_id, f"/undo of change #{log['id']}").strip()

    return ["the ledger row is marked void and kept; nothing is deleted",
            f"{ticker}: in_portfolio is set again from the ledger (a dated card note if it changes)"], do


UNDO["bought"] = _undo_trade
UNDO["sold"] = _undo_trade


# --- gold and BES ----------------------------------------------------------------------------------------------------

def _rate(conn, day: str) -> tuple[str, float]:
    from agents.portfolio.marketdata import usdtry_on

    got = usdtry_on(conn, day)
    if got is None:
        raise Refused("No USD/TRY rate is stored yet; run the price job first (uv run python -m shared.prices).")
    return got


def _grams(conn) -> float:
    return conn.execute("SELECT coalesce(sum(grams), 0) FROM other_assets WHERE kind='gold' AND void=0").fetchone()[0]


def _gold(conn, args):
    from agents.portfolio.marketdata import gold_gram_usd

    if len(args) != 2:
        raise Refused("usage: /gold 1 4689   (grams, TL per gram; a sale: minus grams)")
    grams, price = _num(args[0], "the grams"), _num(args[1], "the TL price per gram")
    if grams == 0 or price <= 0:
        raise Refused("The grams must not be 0 and the price must be above 0.")
    day = clock.today_local()
    rate_day, rate = _rate(conn, day)
    have = _grams(conn)
    if have + grams < -1e-9:
        raise Refused(f"You hold {have:g} g of gold; a sale of {-grams:g} g is more than that.")
    usd = grams * price / rate
    what = "purchase" if grams > 0 else "sale"
    preview = [f"a gold {what}: {abs(grams):g} g at {price:,.2f} TL/g on {day} = {abs(grams) * price:,.2f} TL "
               f"= ${abs(usd):,.2f} (USD/TRY {rate:.4f} of {rate_day})"]
    world = gold_gram_usd(conn, day)
    if world is None:
        preview.append("no world gold price is stored: the price is not checked")
    else:
        gram_try = world[1] * rate
        gap = price / gram_try - 1
        preview.append((f"⚠ {price:,.2f} TL/g is {gap:+.0%} from the world gram price on {world[0]} ({gram_try:,.2f} TL) — "
                        "are you sure?") if abs(gap) > PRICE_GAP else
                       f"price checked: {gap:+.1%} from the world gram price on {world[0]} ({gram_try:,.2f} TL; a bank "
                       "sells a little higher)")

    def apply(conn, number):
        cur = conn.execute("INSERT INTO other_assets (kind, date, grams, price_try, usdtry, command_id, created_at) "
                           "VALUES ('gold', ?, ?, ?, ?, ?, ?)", (day, grams, price, rate, number, clock.utc_iso()))
        return Applied(f"Gold {what} recorded: {abs(grams):g} g at {price:,.2f} TL/g ({have + grams:g} g now).",
                       "other_assets", cur.lastrowid)

    return Plan(preview, ["gold", *args], apply)


def _undo_gold(conn, log: dict):
    row = conn.execute("SELECT grams, void FROM other_assets WHERE id=?", (log["target_id"],)).fetchone()
    if row is None or row[1]:
        raise Refused(f"Change #{log['id']}: its row is not there or already void.")
    if _grams(conn) - row[0] < -1e-9:
        raise Refused(f"Without change #{log['id']} your gold would be below 0 g; undo the later sale first.")

    def do(conn, undo_id):
        conn.execute("UPDATE other_assets SET void=1, voided_by=? WHERE id=?", (undo_id, log["target_id"]))
        return ""

    return ["the row is marked void and kept; nothing is deleted"], do


UNDO["gold"] = _undo_gold


def _bes(conn, args):
    if len(args) != 2:
        raise Refused("usage: /bes 8670 245000   (this month's payment, the BES total; TL)")
    payment, total = _num(args[0], "the payment"), _num(args[1], "the BES total")
    if payment < 0 or total <= 0:
        raise Refused("The payment must be 0 or more and the total above 0.")
    day = clock.today_local()
    rate_day, rate = _rate(conn, day)
    preview = [f"a BES row on {day}: payment {payment:,.2f} TL · total {total:,.2f} TL = ${total / rate:,.2f} "
               f"(USD/TRY {rate:.4f} of {rate_day})"]
    last = conn.execute("SELECT total_try, date FROM other_assets WHERE kind='bes' AND void=0 ORDER BY date DESC, id DESC "
                        "LIMIT 1").fetchone()
    if last and abs(total / last[0] - 1) > BES_GAP:
        preview.append(f"⚠ the total is {total / last[0] - 1:+.0%} from the last one ({last[0]:,.2f} TL on {last[1]}) — "
                       "are you sure?")

    def apply(conn, number):
        cur = conn.execute("INSERT INTO other_assets (kind, date, payment_try, total_try, usdtry, command_id, created_at) "
                           "VALUES ('bes', ?, ?, ?, ?, ?, ?)", (day, payment, total, rate, number, clock.utc_iso()))
        return Applied(f"BES recorded: payment {payment:,.2f} TL · total {total:,.2f} TL.", "other_assets", cur.lastrowid)

    return Plan(preview, ["bes", *args], apply)


def _portfolio(conn, args):
    from agents.portfolio import run

    if args:
        raise Refused("usage: /portfolio")
    return run.on_demand(conn)


register(Command("portfolio", "Holdings, benchmark against SPY and gold, total wealth", "/portfolio", phase=3,
                 info=_portfolio))
register(Command("bought", "Record a buy: quantity, ticker, price", "/bought 10 KO 85.65", changes=True, phase=3,
                 plan=_bought))
register(Command("sold", "Record a sale: quantity, ticker, price", "/sold 5 KO 92.10", changes=True, phase=3, plan=_sold))
register(Command("gold", "Record a gold purchase: grams and TL price per gram", "/gold 1 4689", changes=True, phase=3,
                 plan=_gold))
register(Command("bes", "Record this month's BES payment and the BES total (TL)", "/bes 8670 245000", changes=True,
                 phase=3, plan=_bes))
