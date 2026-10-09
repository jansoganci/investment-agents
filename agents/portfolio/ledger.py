"""The ledger (`holdings`, agent 4 rule 1): one row per event, append-only.

- `buy` and `sell` come from my commands (`/bought`, `/sold`); a wrong one is marked `void` by `/undo`, never deleted.
- `dividend` and `split` are added by code from Yahoo's history in `prices`: a dividend = the dividend per share × the shares I
  held on the ex-date (bought before it) × (1 − withholding); a split multiplies the shares I held on its day.
- Positions (quantity, average cost) are computed by replaying the rows in date order. The dividends and splits are worked out
  again on every replay from `prices` and the buy / sell rows, so a late or cancelled buy never leaves a wrong dividend:
  `sync` writes what changed (a stale code row is marked `void` and the right one added).

Average cost: a buy adds its cost (quantity × price + fee); a sale takes out its share of the cost at the average; a split
changes the shares, not the cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from shared import clock, config
from agents.portfolio.marketdata import Series

EPS = 1e-9
ORDER = {"split": 0, "dividend": 1, "buy": 2, "sell": 3}  # on the same day: the split (at the open), the ex-date, then trades


def withholding() -> float:
    return float(config.settings()["portfolio"]["dividend_withholding"])


@dataclass
class Position:
    stock_id: int
    ticker: str
    quantity: float = 0.0
    cost: float = 0.0          # USD, what the shares still held cost (fees included)

    @property
    def average_cost(self) -> float | None:
        return self.cost / self.quantity if self.quantity > EPS else None


@dataclass
class Ledger:
    positions: dict[int, Position] = field(default_factory=dict)
    flows: list[tuple[str, float, str, int]] = field(default_factory=list)   # (day, USD, kind, stock_id): − put in, + got back
    derived: list[dict] = field(default_factory=list)                        # dividends and splits worked out by code
    negative: list[tuple[str, str, float]] = field(default_factory=list)     # (ticker, day, quantity) — a sale beyond what I held
    first_buy: str | None = None

    @property
    def put_in(self) -> float:
        return -sum(a for _, a, _, _ in self.flows if a < 0)

    @property
    def got_back(self) -> float:
        return sum(a for _, a, _, _ in self.flows if a > 0)

    def held(self) -> list[Position]:
        return sorted((p for p in self.positions.values() if p.quantity > EPS), key=lambda p: p.ticker)


def user_rows(conn, upto: str | None = None) -> list[dict]:
    sql = ("SELECT h.id, h.kind, h.stock_id, s.ticker, h.date, h.quantity, h.price, coalesce(h.fee, 0) FROM holdings h "
           "JOIN stocks s ON s.id = h.stock_id WHERE h.void = 0 AND h.kind IN ('buy', 'sell')")
    args = []
    if upto:
        sql += " AND h.date <= ?"
        args.append(upto)
    keys = ("id", "kind", "stock_id", "ticker", "date", "quantity", "price", "fee")
    return [dict(zip(keys, r)) for r in conn.execute(sql + " ORDER BY h.date, h.id", args)]


def replay(conn, upto: str | None = None, rows: list[dict] | None = None) -> Ledger:
    """Replay the buy / sell rows (default: every non-void one up to `upto`) with the dividends and splits from `prices`."""
    rows = user_rows(conn, upto) if rows is None else [r for r in rows if not upto or r["date"] <= upto]
    upto = upto or clock.today_local()
    led = Ledger()
    if not rows:
        return led
    led.first_buy = min((r["date"] for r in rows if r["kind"] == "buy"), default=None)
    events = [(r["date"], ORDER[r["kind"]], r["id"], r) for r in rows]
    tickers: dict[int, str] = {}
    first: dict[int, str] = {}
    for r in rows:
        tickers[r["stock_id"]] = r["ticker"]
        if r["kind"] == "buy":
            first[r["stock_id"]] = min(first.get(r["stock_id"], r["date"]), r["date"])
    for sid, start in first.items():
        series = Series(conn, tickers[sid], upto)
        for day, ratio in series.splits:
            if day > start:
                events.append((day, ORDER["split"], 0, {"kind": "split", "stock_id": sid, "date": day, "ratio": ratio}))
        for day, per_share in series.dividends():
            if day > start:
                events.append((day, ORDER["dividend"], 0, {"kind": "dividend", "stock_id": sid, "date": day,
                                                           "per_share": per_share}))
    keep = 1 - withholding()
    for day, _, _, e in sorted(events, key=lambda x: x[:3]):
        sid = e["stock_id"]
        pos = led.positions.setdefault(sid, Position(sid, tickers[sid]))
        if e["kind"] == "buy":
            pos.quantity += e["quantity"]
            pos.cost += e["quantity"] * e["price"] + e["fee"]
            led.flows.append((day, -(e["quantity"] * e["price"] + e["fee"]), "buy", sid))
        elif e["kind"] == "sell":
            avg = pos.cost / pos.quantity if pos.quantity > EPS else 0.0
            pos.cost -= avg * min(e["quantity"], max(pos.quantity, 0.0))
            pos.quantity -= e["quantity"]
            if pos.quantity < -EPS:
                led.negative.append((pos.ticker, day, pos.quantity))
            if abs(pos.quantity) <= EPS:
                pos.quantity, pos.cost = 0.0, 0.0
            led.flows.append((day, e["quantity"] * e["price"] - e["fee"], "sell", sid))
        elif pos.quantity > EPS and e["kind"] == "split":
            before = pos.quantity
            pos.quantity *= e["ratio"]
            led.derived.append({"kind": "split", "stock_id": sid, "ticker": pos.ticker, "date": day,
                                "split_ratio": e["ratio"], "before": before, "after": pos.quantity})
        elif pos.quantity > EPS and e["kind"] == "dividend":
            amount = round(pos.quantity * e["per_share"] * keep, 2)
            led.derived.append({"kind": "dividend", "stock_id": sid, "ticker": pos.ticker, "date": day,
                                "quantity": pos.quantity, "per_share": e["per_share"], "amount": amount})
            led.flows.append((day, amount, "dividend", sid))
    return led


def quantity(conn, stock_id: int, upto: str | None = None, rows: list[dict] | None = None) -> float:
    pos = replay(conn, upto, rows).positions.get(stock_id)
    return pos.quantity if pos else 0.0


def sync(conn, led: Ledger) -> list[str]:
    """Write the code's dividend and split rows that changed; returns the lines to tell me. The caller commits."""
    now = clock.utc_iso()
    have = {}
    for hid, kind, sid, day, amount, ratio, ticker in conn.execute(
            "SELECT h.id, h.kind, h.stock_id, h.date, h.amount, h.split_ratio, s.ticker FROM holdings h "
            "JOIN stocks s ON s.id = h.stock_id WHERE h.void = 0 AND h.kind IN ('dividend', 'split') AND h.command_id IS NULL"):
        have[(kind, sid, day)] = (hid, amount, ratio, ticker)
    lines = []
    want = set()
    for d in led.derived:
        key = (d["kind"], d["stock_id"], d["date"])
        want.add(key)
        old = have.get(key)
        if d["kind"] == "dividend":
            if old and abs((old[1] or 0) - d["amount"]) < 0.005:
                continue
            if old:
                conn.execute("UPDATE holdings SET void = 1 WHERE id = ?", (old[0],))
            conn.execute("INSERT INTO holdings (kind, stock_id, date, quantity, amount, created_at) VALUES "
                         "('dividend', ?, ?, ?, ?, ?)", (d["stock_id"], d["date"], d["quantity"], d["amount"], now))
            lines.append(f"{d['ticker']} dividend {d['date']}: {qty_text(d['quantity'])} shares × ${d['per_share']:.4g} "
                         f"− {withholding():.0%} withholding = ${d['amount']:,.2f}" + (" (corrected)" if old else ""))
        else:
            if old and abs((old[2] or 0) - d["split_ratio"]) < EPS:
                continue
            if old:
                conn.execute("UPDATE holdings SET void = 1 WHERE id = ?", (old[0],))
            conn.execute("INSERT INTO holdings (kind, stock_id, date, split_ratio, created_at) VALUES ('split', ?, ?, ?, ?)",
                         (d["stock_id"], d["date"], d["split_ratio"], now))
            lines.append(f"{d['ticker']} split {_ratio(d['split_ratio'])} — your {qty_text(d['before'])} shares are now "
                         f"{qty_text(d['after'])}; check it in Midas")
    for key, (hid, _, _, ticker) in have.items():
        if key not in want:  # its buy was cancelled or moved: the code row no longer holds
            conn.execute("UPDATE holdings SET void = 1 WHERE id = ?", (hid,))
            lines.append(f"{ticker} {key[0]} of {key[2]} withdrawn (no shares were held that day any more)")
    return lines


def qty_text(q: float) -> str:
    return f"{q:,.0f}" if abs(q - round(q)) < 1e-6 else f"{q:,.4f}".rstrip("0")


def _ratio(r: float) -> str:
    return f"{r:g}:1" if r >= 1 else f"1:{1 / r:g}"
