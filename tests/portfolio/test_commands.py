"""Phase 3 commands: /bought /sold /gold /bes and their /undo."""

from agents.analysis import card
from shared import commands, drive
from tests.portfolio.helpers import do, freeze, make_card, price, prices, stock


def setup(db, monkeypatch):
    stock(db, "KO", company="Coca-Cola Co")
    prices(db, "KO", [("2026-10-07", 70.0), ("2026-10-08", 71.0)])
    freeze(monkeypatch, "2026-10-09")


def held(db):
    from agents.portfolio import ledger

    return ledger.quantity(db, 1)


def test_bought_previews_then_records_and_marks_the_card(db, env, monkeypatch):
    setup(db, monkeypatch)
    make_card("KO", "Coca-Cola Co")
    code, text = commands.run(["bought", "10", "KO", "71.50", "2026-10-08", "1.25"])
    assert code == 0 and text.startswith("CONFIRM")
    assert "a buy row: 10 KO at $71.50 on 2026-10-08 + fee $1.25 = $716.25" in text
    assert "price checked: +0.7% from KO's close on 2026-10-08" in text
    assert "KO goes into the portfolio" in text
    assert db.execute("SELECT count(*) FROM holdings").fetchone()[0] == 0
    code, text = do("bought", "10", "KO", "71.50", "2026-10-08", "1.25")
    assert code == 0 and "change #1" in text and "In portfolio: yes." in text
    assert db.execute("SELECT kind, date, quantity, price, fee, command_id FROM holdings").fetchall() == [
        ("buy", "2026-10-08", 10, 71.5, 1.25, 1)]
    assert db.execute("SELECT in_portfolio FROM stocks").fetchone()[0] == "yes"
    head, body = card.split(drive.find_card("KO").read_text())
    assert head["in_portfolio"] == "yes" and "In portfolio: no → yes (/bought, change #1)" in body


def test_refusals_and_are_you_sure(db, monkeypatch):
    setup(db, monkeypatch)
    code, text = commands.run(["bought", "10", "ZZZ", "5"])
    assert code == 1 and "unknown ticker is refused" in text
    assert commands.run(["bought", "10", "KO", "-5"])[0] == 1
    assert commands.run(["bought", "10", "KO", "70", "2026-10-10"])[0] == 1  # in the future
    code, text = commands.run(["bought", "10", "KO", "90"])  # today 2026-10-09 → the close of 2026-10-08
    assert code == 0 and "⚠ $90.00 is +27% from KO's close on 2026-10-08 ($71.00) — are you sure?" in text
    code, text = commands.run(["bought", "10", "KO", "50", "2026-09-01"])
    assert "no close of KO is stored for 2026-09-01: the price is not checked" in text


def test_sold_cannot_exceed_what_i_hold(db, env, monkeypatch):
    setup(db, monkeypatch)
    make_card("KO", "Coca-Cola Co")
    do("bought", "10", "KO", "70", "2026-10-07")
    code, text = do("sold", "11", "KO", "71")
    assert code == 1 and "You hold 10 KO" in text
    code, text = do("sold", "5", "KO", "71", "2026-10-06")  # before the buy
    assert code == 1 and "You hold 0 KO on 2026-10-06" in text
    assert do("sold", "4", "KO", "71")[0] == 0
    code, text = do("sold", "6", "KO", "71")
    assert code == 0 and "0 left. In portfolio: no." in text
    assert db.execute("SELECT in_portfolio FROM stocks").fetchone()[0] == "no"
    assert "In portfolio: yes → no (/sold, change #3)" in drive.find_card("KO").read_text()


def test_undo_of_a_wrong_buy_then_the_right_one(db, env, monkeypatch):
    """Plain sentence "my KO buy was wrong, 10 not 100" → /undo of the wrong row + the right /bought, each after my yes."""
    setup(db, monkeypatch)
    make_card("KO", "Coca-Cola Co")
    do("bought", "100", "KO", "71")
    code, text = commands.run(["undo"])
    assert code == 0 and "cancel change #1: /bought 100 KO 71" in text and "nothing is deleted" in text
    assert held(db) == 100  # nothing changes before yes
    code, text = do("undo", "1")
    assert code == 0 and "Cancelled change #1" in text and "In portfolio: no." in text
    assert held(db) == 0
    do("bought", "10", "KO", "71")
    assert held(db) == 10
    assert db.execute("SELECT quantity, void, voided_by FROM holdings ORDER BY id").fetchall() == [(100, 1, 2), (10, 0, None)]
    assert db.execute("SELECT in_portfolio FROM stocks").fetchone()[0] == "yes"
    body = drive.find_card("KO").read_text()
    assert "In portfolio: yes → no (/undo of change #1, change #2)" in body and "In portfolio: no → yes (/bought, change #3)" in body


def test_undo_of_a_buy_a_later_sale_needs_is_refused(db, monkeypatch):
    setup(db, monkeypatch)
    do("bought", "10", "KO", "70", "2026-10-07")
    do("sold", "5", "KO", "71")
    code, text = do("undo", "1")
    assert code == 1 and "undo that sale first" in text
    assert do("undo", "2")[0] == 0 and do("undo", "1")[0] == 0
    assert held(db) == 0


def test_gold(db, monkeypatch):
    freeze(monkeypatch, "2026-10-09")
    code, text = do("gold", "1", "4689")
    assert code == 1 and "No USD/TRY rate" in text
    price(db, "TRY=X", "2026-10-08", 42.0)
    price(db, "GC=F", "2026-10-08", 3500.0)  # 3,500 / 31.1035 × 42 = 4,726.23 TL per gram
    code, text = commands.run(["gold", "1", "4689"])
    assert "a gold purchase: 1 g at 4,689.00 TL/g on 2026-10-09 = 4,689.00 TL = $111.64 (USD/TRY 42.0000 of 2026-10-08)" in text
    assert "price checked: -0.8% from the world gram price" in text
    assert "are you sure" in commands.run(["gold", "1", "6000"])[1]
    assert do("gold", "2", "4689")[0] == 0
    code, text = do("gold", "-3", "4700")
    assert code == 1 and "You hold 2 g" in text
    assert do("gold", "-1", "4700")[0] == 0
    assert db.execute("SELECT grams, price_try, usdtry FROM other_assets ORDER BY id").fetchall() == [
        (2, 4689, 42.0), (-1, 4700, 42.0)]
    code, text = do("undo", "1")  # the purchase: without it the later sale would leave −1 g
    assert code == 1 and "below 0 g" in text


def test_bes(db, monkeypatch):
    freeze(monkeypatch, "2026-10-09")
    price(db, "TRY=X", "2026-10-08", 42.0)
    assert do("bes", "8670", "245000")[0] == 0
    code, text = commands.run(["bes", "8670", "400000"])
    assert "⚠ the total is +63% from the last one (245,000.00 TL on 2026-10-09) — are you sure?" in text
    assert "are you sure" not in commands.run(["bes", "8670", "253000"])[1]
    assert do("undo", "1")[0] == 0
    assert db.execute("SELECT void FROM other_assets").fetchone()[0] == 1
