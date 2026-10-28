"""shared/prices/mof: Japan's 10-year yield from the Ministry of Finance's CSV (stand-in text in the file's known layout; the first
real read is the Air check)."""

from datetime import datetime, timezone

import pytest

from shared.prices import mof

NOW = datetime(2026, 10, 28, 6, 0, tzinfo=timezone.utc)

CURRENT = """Interest Rate (Percent per annum),,,,
Date,1Y,2Y,10Y,20Y
2026/10/1,0.80,1.00,2.10,2.90
2026/10/2,-,1.10,-,3.00
2026/10/27,0.90,1.20,2.35,3.10
"""

HISTORY = """Interest Rate (Percent per annum),,,,
Date,1Y,2Y,10Y,20Y
1990/1/4,6.0,6.1,6.4,6.5
2026/5/1,0.5,0.6,1.5,2.0
2026/9/25,0.8,1.0,2.00,2.9
2026/10/27,0.9,1.2,2.35,3.1
"""


def reader(texts):
    asked = []

    def get_text(url, timeout=30):
        asked.append(url)
        return texts[url]
    get_text.asked = asked
    return get_text


def test_parse_reads_the_10y_column_and_skips_days_without_a_figure():
    assert mof.parse(CURRENT) == [("2026-10-01", 2.10), ("2026-10-27", 2.35)]


def test_parse_refuses_a_file_it_does_not_know():
    with pytest.raises(mof.MofError, match="no `Date` header"):
        mof.parse("<html>maintenance</html>")
    with pytest.raises(mof.MofError, match="no `10Y` column"):
        mof.parse("Date,1Y,2Y\n2026/10/27,0.9,1.2\n")


def test_a_negative_yield_is_real_and_an_old_odd_row_does_not_stop_the_read(db):
    # the real file goes back to 1974 and holds negative yields (2016–2020); only the days we keep are checked
    text = "Date,10Y\n1974/9/24,99.0\n2016/2/9,-0.02\n2026/10/27,2.35\n"
    assert mof.parse(text)[1] == ("2016-02-09", -0.02)
    assert mof.update(db, reader({mof.ALL_URL: text}), NOW) == 1


def test_an_implausible_figure_on_a_kept_day_is_refused(db):
    with pytest.raises(mof.MofError, match="not a plausible yield"):
        mof.update(db, reader({mof.ALL_URL: "Date,10Y\n2026/10/27,235\n"}), NOW)
    assert db.execute("SELECT count(*) FROM prices WHERE symbol='JP10Y'").fetchone() == (0,)


def test_the_first_read_takes_the_whole_history_and_keeps_120_days(db):
    get = reader({mof.ALL_URL: HISTORY})
    assert mof.update(db, get, NOW) == 2
    assert get.asked == [mof.ALL_URL]
    assert db.execute("SELECT date, close, currency, source FROM prices WHERE symbol='JP10Y' ORDER BY date").fetchall() == [
        ("2026-09-25", 2.0, "%", "mof"), ("2026-10-27", 2.35, "%", "mof")]


def test_later_reads_use_the_small_file_and_never_overwrite(db):
    mof.update(db, reader({mof.ALL_URL: HISTORY}), NOW)
    get = reader({mof.CURRENT_URL: CURRENT})
    assert mof.update(db, get, NOW) == 1                      # only 2026-10-01 is new; 10-27 is stored
    assert get.asked == [mof.CURRENT_URL]
    assert mof.update(db, get, NOW) == 0
    assert db.execute("SELECT close FROM prices WHERE symbol='JP10Y' AND date='2026-10-27'").fetchone() == (2.35,)


def test_a_future_date_is_not_stored(db):
    get = reader({mof.ALL_URL: HISTORY + "2026/12/1,0.9,1.2,2.50,3.1\n"})
    assert mof.update(db, get, NOW) == 2


def test_an_unreachable_file_is_a_mof_error(db):
    def down(url, timeout=30):
        raise mof.MofError("the Ministry of Finance file could not be reached (URLError)")
    with pytest.raises(mof.MofError, match="could not be reached"):
        mof.update(db, down, NOW)
    assert db.execute("SELECT count(*) FROM prices WHERE symbol='JP10Y'").fetchone() == (0,)
