"""Fixes from the phase 1 audit (2026-10-05): identity by CIK, the write lock, the weekly check, the card file."""

import sqlite3

import pytest
import yaml

from agents.analysis import card, run
from shared import commands, config, drive, prices
from shared.commands import stocks
from tests.fixtures.loader import FixtureSources


class Renamed(FixtureSources):
    """SEC now lists Coca-Cola under a new ticker, KOX (like FB → META)."""

    def lookup(self, ticker):
        if ticker.upper() == "KOX":
            return {"cik": "0000021344", "name": "COCA COLA CO", "ticker": "KOX", "exchange": "NYSE", "all_tickers": ["KOX"]}
        return super().lookup(ticker)


class TwoClasses(FixtureSources):
    """Coca-Cola with a second share class, KOB (like GOOG next to GOOGL)."""

    def lookup(self, ticker):
        if ticker.upper() == "KOB":
            return {"cik": "0000021344", "name": "COCA COLA CO", "ticker": "KOB", "exchange": "NYSE",
                    "all_tickers": ["KO", "KOB"]}
        return super().lookup(ticker)


def test_a_renamed_ticker_keeps_the_stock_and_the_card(db, env):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    out = run.analyze(db, "KOX", Renamed(), today="2026-10-12")
    assert "Ticker changed: KO → KOX" in out.text
    assert db.execute("SELECT count(*), max(ticker) FROM stocks").fetchone() == (1, "KOX")
    path = drive.find_card("KOX")
    assert path.parent.name.startswith("KOX - ") and drive.find_card("KO") is None
    head, body = card.split(path.read_text())
    assert head["ticker"] == "KOX" and "Ticker: KO → KOX (the same company" in body
    assert body.count("· fundamental · agent_3 ·") == 2  # the history stays on the same card


def test_another_share_class_is_refused(db, env):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    with pytest.raises(run.Refused, match="another share class of KO"):
        run.analyze(db, "KOB", TwoClasses())
    assert db.execute("SELECT count(*) FROM stocks").fetchone()[0] == 1


def test_watch_under_a_new_ticker_relabels(db, env, monkeypatch):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    monkeypatch.setattr(stocks, "SOURCES", Renamed())
    code, text = commands.run(["watch", "KOX"])
    assert "ticker KO → KOX" in text
    code, text = commands.run(["watch", "KOX", "--yes"])
    assert code == 0 and db.execute("SELECT ticker, status FROM stocks").fetchone() == ("KOX", "watching")


class Watchful(FixtureSources):
    """Fails the test if SEC is asked while another writer is locked out."""

    def lookup(self, ticker):
        other = sqlite3.connect(config.db_path(), timeout=0)
        try:
            other.execute("BEGIN IMMEDIATE")  # would fail if the command held the write lock
            other.rollback()
        finally:
            other.close()
        return super().lookup(ticker)


def test_sec_is_never_asked_inside_the_write_lock(db, monkeypatch):
    monkeypatch.setattr(stocks, "SOURCES", Watchful())
    code, text = commands.run(["watch", "KO", "--yes"])
    assert code == 0, text
    code, text = commands.run(["analyze", "PFE", "--yes"])
    assert code == 0, text


def test_analyze_refuses_an_unknown_ticker_in_the_preview(db, monkeypatch):
    monkeypatch.setattr(stocks, "SOURCES", FixtureSources())
    code, text = commands.run(["analyze", "ZZZZ"])
    assert code == 1 and "does not know" in text
    assert db.execute("SELECT count(*) FROM command_log").fetchone()[0] == 0


class Broken(FixtureSources):
    def submissions(self, cik):
        if int(cik) == 21344:
            raise OSError("Drive folder not reachable")
        return super().submissions(cik)


def test_weekly_goes_on_after_an_unexpected_error(db, env):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    run.analyze(db, "PFE", FixtureSources(), today="2026-10-05")
    db.execute("UPDATE stocks SET status='watching'")
    db.execute("UPDATE card_entries SET filing='older'")
    db.commit()
    msg = run.weekly(db, Broken(), today="2026-10-12")
    assert "KO: OSError" in msg and "ANALYSIS · PFE" in msg


def test_unknown_header_fields_are_kept_and_unclear_is_written(tmp_path):
    path = tmp_path / "card.md"
    card.write(path, "---\nticker: X\nstatus: watching\nmy_field: keep me\n---\n# X\n")
    card.append(path, card.note_entry("2026-10-05", "hello"), {"lynch_type": "unclear"})
    head, _ = card.split(path.read_text())
    assert head["my_field"] == "keep me" and head["lynch_type"] == "unclear"
    assert not list(tmp_path.glob("*.tmp"))  # written at once through a temporary file


def test_the_card_shows_the_5_year_free_cash_path(db, env):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    text = drive.find_card("KO").read_text()
    data = yaml.safe_load(text.split("```yaml\n", 1)[1].split("\n```", 1)[0])
    assert len(data["free_cash"]["path_5y"]) == 5


def test_financials_are_never_deleted(db, env):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM financials")


class Recorder:
    def __init__(self):
        self.calls = []

    def chart(self, symbol, range_, interval):
        self.calls.append(range_)
        from tests.test_prices import chart
        return chart(["2026-09-30"], [10.0], symbol=symbol)


def test_a_symbol_with_only_recent_rows_still_gets_its_10_years(db):
    db.execute("INSERT INTO prices (symbol, date, close, created_at) VALUES ('KO', '2026-09-29', 60, 'x')")
    db.commit()
    src = Recorder()
    prices.ensure_history(db, "KO", src)
    assert src.calls == ["10y"]
