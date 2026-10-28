"""shared/bulletin/gather: the window, my stocks and their thesis breaks, the posts, SEC filings, earnings dates, web searches —
all against stand-ins, no network and no model."""

import json
from datetime import datetime, timezone

import pytest

from shared import clock, drive
from shared.bulletin import gather
from shared.prices import yahoo
from shared.search import Hit, SearchError

NOW = datetime(2026, 10, 28, 5, 0, tzinfo=timezone.utc)          # 08:00 Turkey time, a Wednesday
SINCE = "2026-10-27T05:15:00Z"                                   # Tuesday's bulletin time


def card_text(breaks=("price war", "debt grows", "CEO leaves")):
    return ("---\nticker: KO\n---\n\n## 2026-10-20 · fundamental · agent_3 · 10-K FY2025\n### Thesis\nWhy it is owned:\n1. brands\n"
            "What would break it:\n" + "\n".join(f"{i}. {b}" for i, b in enumerate(breaks, 1)) + "\n")


def add_stock(db, ticker, company, status="watching", held="no", cik=None, card=None):
    db.execute("INSERT INTO stocks (ticker, company, status, in_portfolio, cik, created_at) VALUES (?, ?, ?, ?, ?, 'x')",
               (ticker, company, status, held, cik))
    db.commit()
    if card:
        path = drive.card_path(ticker, company)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(card, encoding="utf-8")


def add_post(db, n, when, title="A post", site="emtia", tags=(), sentence="One sentence.", text="Body text.", missing=0):
    db.execute("INSERT INTO articles (id, url, site, title, published_at, tags, sentence, full_text, text_missing, created_at) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'x')",
               (n, f"https://{site}.example/p{n}", site, title, when, json.dumps(list(tags)), sentence, text, missing))
    db.commit()


def add_tag(db, tag, ticker, status="confirmed"):
    db.execute("INSERT INTO tags (tag, kind, maps_to, us_listed, status, created_at) VALUES (?, 'company', ?, 1, ?, 'x')",
               (tag, ticker, status))
    db.commit()


# --- the window -----------------------------------------------------------------------------------------------------------

def test_the_window_starts_at_the_last_weekdays_bulletin_time():
    def start(day, hour=5):
        return clock.utc_iso(gather.window_start(datetime(2026, 10, day, hour, 0, tzinfo=timezone.utc)))
    assert start(28) == SINCE                                 # Wednesday → Tuesday 08:15 Turkey time
    assert start(26) == "2026-10-23T05:15:00Z"                # Monday → Friday: the weekend is inside
    assert start(25) == "2026-10-23T05:15:00Z"                # Sunday → Friday
    assert start(28, hour=19) == SINCE                        # the same day later: still since Tuesday


# --- my stocks ------------------------------------------------------------------------------------------------------------

def test_breaks_are_read_from_the_newest_thesis():
    assert gather.breaks_of(card_text()) == ("2026-10-20", ("price war", "debt grows", "CEO leaves"))
    assert gather.breaks_of("---\nticker: KO\n---\n") == (None, ())


def test_held_stocks_come_first_and_only_held_or_watched_ones(db, env):
    add_stock(db, "NVDA", "Nvidia", card=card_text(("a", "b", "c")))
    add_stock(db, "KO", "Coca-Cola", held="yes", card=card_text())
    add_stock(db, "SNAP", "Snap", status="candidate")
    add_stock(db, "OLD", "Old Co", status="archived")
    add_stock(db, "NOCARD", "No Card Inc")
    stocks = gather.my_stocks(db)
    assert [(s.ticker, s.held) for s in stocks] == [("KO", True), ("NOCARD", False), ("NVDA", False)]
    assert stocks[0].breaks == ("price war", "debt grows", "CEO leaves") and stocks[0].thesis_date == "2026-10-20"
    assert stocks[1].breaks == () and stocks[1].thesis_date is None


# --- posts ----------------------------------------------------------------------------------------------------------------

def test_posts_are_those_since_the_window_and_know_my_stocks(db):
    add_tag(db, "Coca-Cola", "KO")
    add_tag(db, "Pepsi", "PEP", status="waiting")
    add_post(db, 1, "2026-10-26T10:00:00Z", "Too old")
    add_post(db, 2, "2026-10-27T06:00:00Z", "Cola news", tags=["Coca-Cola", "Pepsi", "Gıda"], text="Sales rose 5%.")
    add_post(db, 3, "2026-10-28T03:00:00Z", "Macro wrap", site="dragonomi")
    found = gather.posts(db, SINCE, {"KO", "PEP"})
    assert [p.id for p in found] == ["P3", "P2"]                    # newest first; P1 is before the window
    cola = found[1]
    assert cola.tickers == ("KO",)                                  # the waiting tag is not trusted
    assert "Cola news" in cola.text and "Tags: Coca-Cola, Pepsi, Gıda" in cola.text and "Sales rose 5%." in cola.text
    assert found[0].site == "dragonomi" and found[0].tickers == ()


def test_only_the_first_posts_get_their_text_and_mine_come_first(db):
    add_tag(db, "Coca-Cola", "KO")
    for n in range(1, 6):
        add_post(db, n, f"2026-10-27T1{n}:30:00Z", f"Post {n}", text=f"BODY{n}" + "x" * 50)
    add_post(db, 9, "2026-10-27T06:10:00Z", "Mine but the oldest", tags=["Coca-Cola"], text="BODY9")
    found = {p.id: p for p in gather.posts(db, SINCE, {"KO"}, {"full_posts": 3, "post_chars": 8})}
    full = [i for i, p in found.items() if "BODY" in p.text]
    assert set(full) == {"P9", "P5", "P4"}                         # my stock's post, then the two newest
    assert "BODY5xxx" in found["P5"].text and "BODY5xxxx" not in found["P5"].text   # cut at post_chars
    assert "BODY1" not in found["P1"].text and "One sentence." in found["P1"].text


def test_a_post_the_site_cut_says_so(db):
    add_post(db, 1, "2026-10-27T06:00:00Z", "Paywalled", text="", missing=1)
    assert "cut this post for non-members" in gather.posts(db, SINCE, set())[0].text


# --- SEC filings ----------------------------------------------------------------------------------------------------------

def submissions_of(rows):
    keys = ("form", "filingDate", "acceptanceDateTime", "items", "accessionNumber", "primaryDocument")
    return {"filings": {"recent": {k: [r[i] for r in rows] for i, k in enumerate(keys)}}}


def test_new_filings_are_found_by_acceptance_time_and_described(db):
    rows = [("10-Q", "2026-10-27", "2026-10-27T16:05:22.000Z", "", "0000021344-26-000010", "ko-10q.htm"),
            ("8-K", "2026-10-28", "2026-10-28T01:00:00.000Z", "2.02,9.01", "0000021344-26-000011", "ko-8k.htm"),
            ("8-K", "2026-10-28", "2026-10-28T02:00:00.000Z", "9.01", "0000021344-26-000012", "ko-ex.htm"),
            ("8-K", "2026-10-27", "2026-10-27T04:00:00.000Z", "5.02", "0000021344-26-000009", "ko-old.htm"),   # before the window
            ("4", "2026-10-28", "2026-10-28T02:30:00.000Z", "", "0000021344-26-000013", "form4.xml")]
    stocks = [gather.StockInfo("KO", "Coca-Cola", True, None, ())]
    pieces, notes = gather.filings(stocks, {"KO": "0000021344"}, SINCE, lambda cik: submissions_of(rows))
    assert notes == [] and [p.id for p in pieces] == ["F1", "F2"]
    assert pieces[0].text == "KO filed a 10-Q on 2026-10-27. Agent 3 reads new 10-K / 10-Q filings on Sunday."
    assert pieces[1].text == "KO filed an 8-K on 2026-10-28: reported its results (item 2.02)."
    assert pieces[1].url.endswith("/000002134426000011/ko-8k.htm") and pieces[1].tickers == ("KO",)


def test_a_filing_without_a_time_is_judged_by_its_date_and_a_sec_error_is_a_note(db):
    stocks = [gather.StockInfo("KO", "Coca-Cola", True, None, ()), gather.StockInfo("V", "Visa", False, None, ())]

    def sub(cik):
        if cik == "2":
            raise RuntimeError("SEC answered 503")
        return {"filings": {"recent": {"form": ["20-F", "10-K"], "filingDate": ["2026-10-28", "2026-10-01"]}}}
    pieces, notes = gather.filings(stocks, {"KO": "1", "V": "2"}, SINCE, sub)
    assert [p.text[:30] for p in pieces] == ["KO filed a 20-F on 2026-10-28."]
    assert notes == ["SEC could not be asked for V: RuntimeError"]


# --- earnings dates -------------------------------------------------------------------------------------------------------

def test_earnings_dates_within_the_next_days(db):
    stocks = [gather.StockInfo(t, t, False, None, ()) for t in ("KO", "NVDA", "FCX", "BAD")]
    dates = {"KO": ["2026-10-30"], "NVDA": ["2026-11-17"], "FCX": ["2027-01-21"]}

    def fetch(ticker):
        if ticker == "BAD":
            raise yahoo.YahooError("429")
        return dates[ticker]
    pieces, notes = gather.earnings(stocks, "2026-10-28", 45, fetch)
    assert [(p.id, p.text) for p in pieces] == [("E1", "KO reports earnings on 2026-10-30 (Yahoo)."),
                                                 ("E2", "NVDA reports earnings on 2026-11-17 (Yahoo).")]
    assert notes == ["Yahoo has no earnings date for BAD (YahooError)"]


def test_yahoo_next_earnings_reads_the_calendar(monkeypatch):
    from datetime import date

    class Fake:
        def Ticker(self, symbol):
            class T:
                calendar = {"Earnings Date": [date(2026, 11, 17), date(2026, 11, 16)]}
            return T()
    monkeypatch.setattr(yahoo, "_yf", lambda: Fake())
    monkeypatch.setattr(yahoo, "_space", lambda: None)
    assert yahoo.next_earnings("NVDA") == ["2026-11-16", "2026-11-17"]

    class Empty:
        def Ticker(self, symbol):
            class T:
                calendar = {}
            return T()
    monkeypatch.setattr(yahoo, "_yf", lambda: Empty())
    assert yahoo.next_earnings("X") == []


# --- web searches ---------------------------------------------------------------------------------------------------------

def hit(url, title="T", date="2026-10-28T01:00:00+00:00", site="Example", summary="S"):
    return Hit(title, url, site, date, "snip", summary, 2.0, 3)


CONFIG = {"max_searches": 5, "search_count": 4, "interests": [{"topic": "oil", "query": "Brent crude oil"},
                                                               {"topic": "japan", "query": "Bank of Japan JGB yield"}]}


def test_searches_go_held_stocks_then_interests_then_watched_and_stop_at_the_budget():
    stocks = [gather.StockInfo("KO", "Coca-Cola", True, None, ()), gather.StockInfo("NVDA", "Nvidia", False, None, ()),
              gather.StockInfo("FCX", "Freeport", False, None, ())]
    asked = []

    def fake(query, **kw):
        asked.append((query, kw["count"], kw["after"]))
        return [hit(f"https://x/{len(asked)}")]
    pieces, notes, made = gather.web(stocks, SINCE, CONFIG, fake)
    assert [a[0] for a in asked] == ["Coca-Cola stock news", "Brent crude oil", "Bank of Japan JGB yield", "Nvidia stock news",
                                     "Freeport stock news"]
    assert asked[0][1:] == (4, "2026-10-26") and made == 5 and notes == []      # `after` = the day before the window starts
    assert [(p.id, p.topic, p.tickers) for p in pieces][:2] == [("W1", "KO", ("KO",)), ("W2", "oil", ())]
    tight = gather.web(stocks, SINCE, dict(CONFIG, max_searches=2), fake)
    assert tight[2] == 2


def test_hits_are_deduplicated_and_old_ones_dropped():
    stocks = [gather.StockInfo("KO", "Coca-Cola", True, None, ())]
    answers = iter([[hit("https://x/a", "A"), hit("https://x/old", "Old", date="2026-10-20T00:00:00+00:00"),
                     hit("https://x/nodate", "No date", date=None)],
                    [hit("https://x/a", "A again"), hit("https://x/b", "B", site=None)]])
    pieces, notes, made = gather.web(stocks, SINCE, dict(CONFIG, max_searches=2, interests=[{"topic": "oil", "query": "Brent"}]),
                                     lambda q, **kw: next(answers))
    assert [(p.id, p.title) for p in pieces] == [("W1", "A"), ("W2", "No date"), ("W3", "B")]
    assert pieces[2].site == "x" and pieces[0].text == "A\nS"


def test_a_failed_search_is_a_note_and_a_dead_key_stops_the_rest():
    stocks = [gather.StockInfo("KO", "Coca-Cola", True, None, ())]
    calls = []

    def flaky(query, **kw):
        calls.append(query)
        if len(calls) == 1:
            raise SearchError("DeepSeek search: HTTP 503, DeepSeek's server is overloaded")
        raise SearchError("DEEPSEEK_API_KEY is not set")
    pieces, notes, made = gather.web(stocks, SINCE, CONFIG, flaky)
    assert pieces == [] and made == 0 and len(calls) == 2           # the key error ended it
    assert notes[0].startswith("Web search 'KO' failed: DeepSeek search: HTTP 503")
    assert "Web search 'oil' failed: DEEPSEEK_API_KEY is not set" in notes and notes[-1] == "The remaining web searches were skipped."


# --- everything -----------------------------------------------------------------------------------------------------------

def test_gather_puts_it_all_in_one_pack(db, env):
    add_stock(db, "KO", "Coca-Cola", held="yes", cik="21344", card=card_text())
    add_tag(db, "Coca-Cola", "KO")
    add_post(db, 7, "2026-10-28T03:00:00Z", "Cola news", tags=["Coca-Cola"])
    rows = [("10-Q", "2026-10-27", "2026-10-27T16:05:22.000Z", "", "0000021344-26-000010", "ko-10q.htm")]
    pack = gather.gather(db, NOW, search_fn=lambda q, **kw: [hit("https://x/1", "Hit")],
                         submissions=lambda cik: submissions_of(rows), earnings_fn=lambda t: ["2026-10-30"])
    assert (pack.window_start, pack.window_end) == (SINCE, "2026-10-28T05:00:00Z")
    assert [s.ticker for s in pack.stocks] == ["KO"] and [p.id for p in pack.posts] == ["P7"]
    assert [p.id for p in pack.filings] == ["F1"] and [p.id for p in pack.earnings] == ["E1"]
    assert pack.searches == 9 and len(pack.web) == 1             # one for KO + the 8 interests; the same URL once
    assert set(pack.pieces()) == {"P7", "W1", "F1", "E1"}
    text = gather.describe(pack)
    assert "my stocks 1 · posts 1 · web hits 1 (9 searches) · filings 1 · earnings dates 1" in text
    assert "KO (held): thesis 2026-10-20, 3 breaks" in text and "P7 · emtia" in text


def test_without_searches_nothing_is_spent(db, env):
    called = []
    pack = gather.gather(db, NOW, search_fn=lambda *a, **k: called.append(1), searches=False,
                         submissions=lambda cik: {}, earnings_fn=lambda t: [])
    assert called == [] and pack.web == [] and pack.searches == 0
