"""shared/bulletin/market: the figures table — the 1-month and day changes, basis points for yields, Turkish numbers."""

import pytest

from shared.bulletin import market
from shared.bulletin.market import Row


def put(db, symbol, *closes):
    for day, close in closes:
        db.execute("INSERT INTO prices (symbol, date, close, adj_close, source, created_at) VALUES (?, ?, ?, ?, 'test', 'x')",
                   (symbol, day, close, close))
    db.commit()


def test_month_before_clamps_the_day():
    assert market.month_before("2026-10-27") == "2026-09-27"
    assert market.month_before("2026-03-31") == "2026-02-28"
    assert market.month_before("2026-01-15") == "2025-12-15"


def test_a_price_changes_in_percent_against_the_last_close_a_month_ago(db):
    # 09-28 is after the date a month before 10-27 (09-27), so the base is 09-25
    put(db, "^GSPC", ("2026-09-25", 7000.0), ("2026-09-28", 7100.0), ("2026-10-26", 7600.0), ("2026-10-27", 7700.0))
    r = market.row(db, "S&P 500", "^GSPC")
    assert (r.day, r.last) == ("2026-10-27", 7700.0)
    assert r.month == pytest.approx(10.0) and r.daily == pytest.approx(1.3158, abs=1e-3)


def test_a_yield_changes_in_basis_points(db):
    put(db, "^TNX", ("2026-09-25", 4.60), ("2026-10-26", 5.00), ("2026-10-27", 5.05))
    r = market.row(db, "ABD 10Y", "^TNX", "yield")
    assert r.month == pytest.approx(45) and r.daily == pytest.approx(5)


def test_without_a_close_a_month_old_there_is_no_month_change(db):
    put(db, "BZ=F", ("2026-10-26", 100.0), ("2026-10-27", 110.0))
    r = market.row(db, "Brent", "BZ=F")
    assert r.month is None and r.daily == pytest.approx(10.0)
    assert market.row(db, "DXY", "DX-Y.NYB").last is None


def test_the_text_is_turkish(db):
    put(db, "^GSPC", ("2026-09-25", 7000.0), ("2026-10-26", 7600.0), ("2026-10-27", 7700.0))
    put(db, "^TNX", ("2026-09-25", 4.60), ("2026-10-26", 5.00), ("2026-10-27", 5.05))
    put(db, "GC=F", ("2026-09-25", 4000.0), ("2026-10-26", 4100.0), ("2026-10-27", 3900.0))
    text = market.render([market.row(db, "S&P 500", "^GSPC"), market.row(db, "ABD 10Y", "^TNX", "yield"),
                          market.row(db, "Altın", "GC=F"), market.row(db, "Brent", "BZ=F")])
    assert text.split("\n") == [
        "📊 RAKAMLAR (son kapanış)",
        "S&P 500 · 7.700,00 · 1 ay ▲ %10,0 · gün ▲ %1,3",
        "ABD 10Y · %5,05 · 1 ay ▲ 45 bp · gün ▲ 5 bp",
        "Altın · 3.900,00 · 1 ay ▼ %2,5 · gün ▼ %4,9",
        "Brent · veri yok",
    ]


def test_a_figure_with_an_older_last_close_shows_its_date(db):
    put(db, "^GSPC", ("2026-10-26", 7600.0), ("2026-10-27", 7700.0))
    put(db, "JP10Y", ("2026-10-23", 2.30), ("2026-10-24", 2.35))
    text = market.render([market.row(db, "S&P 500", "^GSPC"), market.row(db, "Japonya 10Y", "JP10Y", "yield")])
    assert "Japonya 10Y · %2,35 (24.10) ·" in text and "S&P 500 · 7.700,00 ·" in text


def test_a_change_that_rounds_to_nothing_has_no_arrow():
    assert market.change_text("price", 0.02) == "• %0,0"
    assert market.change_text("yield", -0.3) == "• 0 bp"
    assert market.change_text("yield", None) == "—"


def test_the_rows_come_from_settings_in_order(db):
    labels = [r.label for r in market.rows(db)]
    assert labels == ["S&P 500", "Nasdaq", "ABD 10Y", "Japonya 10Y", "Altın", "Brent", "DXY", "USDJPY", "EURJPY", "CHFJPY"]


def test_the_command_prints_the_table(db, capsys):
    from shared.bulletin import __main__ as cli
    put(db, "^GSPC", ("2026-10-26", 7600.0), ("2026-10-27", 7700.0))
    assert cli.main(["--market"]) == 0
    assert capsys.readouterr().out.startswith("📊 RAKAMLAR (son kapanış)\nS&P 500 · 7.700,00")
    assert cli.main(["--bogus"]) == 2


def test_the_gather_command_describes_an_empty_database_without_searching(db, capsys):
    from shared.bulletin import __main__ as cli
    assert cli.main(["--gather", "--no-search"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("GATHERED · window ") and "my stocks 0 · posts 0 · web hits 0 (0 searches) · filings 0 · earnings dates 0" in out
    assert cli.main(["--gather", "--bogus"]) == 2
