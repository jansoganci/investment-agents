"""Agent 4's weekly watches: the drop alert (none in a split week, once per fall), the valuation watch (4 weeks), the new-money
ranking (3 conditions) and the 25% line."""

import json

from agents.portfolio import run
from agents.portfolio.watch import week_end_for
from tests.portfolio.helpers import do, freeze, fridays, fundamental, make_card, price, prices, stock


def weekly(db, monkeypatch, friday):
    from datetime import date, timedelta

    freeze(monkeypatch, (date.fromisoformat(friday) + timedelta(days=2)).isoformat())
    return run.weekly(db)


def signals(db, kind):
    return [(t, d, json.loads(x)) for t, d, x in db.execute(
        "SELECT s.ticker, g.date, g.detail FROM signals g JOIN stocks s ON s.id = g.stock_id WHERE g.kind=? ORDER BY g.id",
        (kind,))]


def test_week_end_is_the_friday_before_the_run():
    assert week_end_for("2026-06-07") == "2026-06-05"   # Sunday
    assert week_end_for("2026-06-06") == "2026-06-05"   # Saturday
    assert week_end_for("2026-06-05") == "2026-05-29"   # Friday: its close is not in yet


def held(db, monkeypatch, ticker="X", day="2026-04-03", at=100.0):
    stock(db, ticker)
    freeze(monkeypatch, day)
    assert do("bought", "10", ticker, str(at), day)[0] == 0


def test_a_drop_of_20_percent_gives_one_pending_alert_per_fall(db, monkeypatch):
    weeks = fridays("2026-04-03", 6)
    prices(db, "X", list(zip(weeks, [100.0, 100.0, 79.0, 78.0, 101.0, 80.0])))
    held(db, monkeypatch)
    for w in weeks:
        text = weekly(db, monkeypatch, w)
    got = signals(db, "drop_alert")
    assert [(t, d) for t, d, _ in got] == [("X", weeks[2]), ("X", weeks[5])]  # not again in week 4; again after a new high
    assert got[0][2]["drop"] == 0.21 and got[0][2]["high"] == 100.0
    assert db.execute("SELECT DISTINCT status FROM signals WHERE kind='drop_alert'").fetchall() == [("pending",)]
    assert f"Drop alerts: X 21% below its 52-week high ($101.00, week of {weeks[4]}) → agent 3 checks the thesis" in text


def test_no_drop_alert_in_a_split_week_even_when_the_rows_look_like_a_drop(db, monkeypatch):
    weeks = fridays("2026-04-03", 3)
    # rows that look unadjusted although stored after the split (the worst case): only the split-week rule stops the alert
    prices(db, "X", [(weeks[0], 100.0, None, None, "2026-04-20"), (weeks[1], 100.0, None, None, "2026-04-20"),
                     ("2026-04-15", 50.0, None, 2.0), (weeks[2], 50.0)])
    held(db, monkeypatch)
    text = weekly(db, monkeypatch, weeks[2])
    assert signals(db, "drop_alert") == []
    assert "X: a split this week — no drop alert (a split looks like a drop)" in text


def test_after_a_split_week_the_old_closes_are_in_the_new_shares(db, monkeypatch):
    weeks = fridays("2026-04-03", 4)
    prices(db, "X", [(weeks[0], 100.0), (weeks[1], 100.0), ("2026-04-15", 50.0, None, 2.0), (weeks[2], 50.0), (weeks[3], 49.0)])
    held(db, monkeypatch)
    for w in weeks:
        weekly(db, monkeypatch, w)
    assert signals(db, "drop_alert") == []  # 100 stored before the split = 50 in today's shares: a 2% fall, not 51%
    assert db.execute("SELECT quantity FROM holdings WHERE kind='buy'").fetchone()[0] == 10
    from agents.portfolio import value

    assert value.compute(db, weeks[3]).holdings[0].quantity == 20


def test_valuation_watch_4_weeks_in_a_row_then_back_of_the_queue(db, env, monkeypatch):
    weeks = fridays("2026-04-03", 6)
    g, h = stock(db, "G"), stock(db, "H")
    make_card("G", "G Inc", fundamental("2026-03-30", 100.0, peg=2.8, fcf_yield=0.02))
    make_card("H", "H Inc", fundamental("2026-03-30", 50.0, peg=1.0, fcf_yield=0.05))
    prices(db, "G", list(zip(weeks, [100.0, 110.0, 110.0, 110.0, 110.0, 110.0])))   # PEG 2.8 → 3.08 from week 2
    prices(db, "H", list(zip(weeks, [50.0] * 6)))
    for w in weeks:
        text = weekly(db, monkeypatch, w)
        if w == weeks[3]:
            assert "Expensive 4 weeks" not in text
    got = signals(db, "expensive")
    assert [(t, d, x["weeks"]) for t, d, x in got] == [("G", weeks[4], 4)]  # once, in the 4th week
    assert "Expensive 4 weeks: G (PEG 3.1 · FCF yield 1.8%)" in text
    body = (env["drive"] / "Stocks" / "G - G Inc" / "card.md").read_text()
    assert "· note · agent_4\nExpensive for 4 weeks in a row (PEG 3.1 · FCF yield 1.8% at the close of " + weeks[4] in body
    assert "not a sell suggestion" in body
    ranks = [(t, x["rank"]) for t, d, x in signals(db, "new_money_rank") if d == weeks[5]]
    assert ranks == [("H", 1), ("G", 2)]  # G is at the back while it stays expensive
    rows = db.execute("SELECT week_end, round(peg, 2), expensive FROM valuations WHERE stock_id=? ORDER BY week_end",
                      (g,)).fetchall()
    assert rows[0] == (weeks[0], 2.8, 0) and rows[1] == (weeks[1], 3.08, 1)


def thesis(db, sid, status):
    db.execute("INSERT INTO card_entries (stock_id, date, record, who, thesis_status, created_at) VALUES "
               "(?, '2026-03-30', 'fundamental', 'agent_3', ?, '2026-03-30T00:00:00Z')", (sid, status))
    db.commit()


def test_new_money_ranks_by_the_three_conditions_then_the_fall(db, env, monkeypatch):
    weeks = fridays("2026-04-03", 2)
    a, b, c, d = stock(db, "A"), stock(db, "B"), stock(db, "C"), stock(db, "D")
    stock(db, "M", grade="mid")  # not on the green list
    for t, sid, peg, status in (("A", a, 1.0, "intact"), ("B", b, 2.5, "intact"), ("C", c, 1.0, "watch"),
                                ("D", d, 1.5, "intact")):
        make_card(t, f"{t} Inc", fundamental("2026-03-30", 100.0, peg=peg, fcf_yield=0.05))
        thesis(db, sid, status)
    prices(db, "A", list(zip(weeks, [100.0, 95.0])))  # 3 conditions, −5%
    prices(db, "B", list(zip(weeks, [100.0, 60.0])))  # PEG 2.5 × 0.6 = 1.5 (fair now): 3 conditions, −40%
    prices(db, "C", list(zip(weeks, [100.0, 50.0])))  # thesis `watch`: 2 conditions, −50%
    prices(db, "D", list(zip(weeks, [100.0, 100.0])))  # at its high: 2 conditions, 0%
    for w in weeks:
        text = weekly(db, monkeypatch, w)
    ranks = [(t, x["rank"], x["score"]) for t, dd, x in signals(db, "new_money_rank") if dd == weeks[1]]
    assert ranks == [("B", 1, 3), ("A", 2, 3), ("C", 3, 2), ("D", 4, 2)]
    assert "New money: 1) B  2) A  3) C  4) D" in text


def test_the_25_percent_line(db, monkeypatch):
    weeks = fridays("2026-04-03", 2)
    stock(db, "A"), stock(db, "B")
    prices(db, "A", list(zip(weeks, [100.0, 80.0])))
    prices(db, "B", list(zip(weeks, [100.0, 99.0])))
    freeze(monkeypatch, weeks[0])
    do("bought", "10", "A", "100", weeks[0])
    for w in weeks:
        text = weekly(db, monkeypatch, w)
    assert "New money: 1) B" in text
    assert "Not suggested (25% rule): A — would rank 1st, 100% of the stock portfolio. Not a sell signal. Your call." in text
    cap = [x for t, dd, x in signals(db, "weight_cap") if dd == weeks[1]]
    assert cap[0]["would_rank"] == 1 and cap[0]["weight"] == 1.0
    assert "sell" not in text.lower().replace("not a sell signal", "")  # agent 4 never says sell
