import json
from datetime import datetime, timedelta, timezone

import pytest

from agents.counter import __main__ as cli
from agents.counter import block, count
from shared import clock

NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)
_n = [0]


def when(days_ago, hours=0):
    return clock.utc_iso(NOW - timedelta(days=days_ago, hours=hours))


def tag(db, name, kind, maps_to=None, us=None, status="confirmed"):
    db.execute("INSERT INTO tags (tag, kind, maps_to, us_listed, source, status, created_at) VALUES (?, ?, ?, ?, 'ai', ?, 'x')",
               (name, kind, maps_to, us, status))
    db.commit()


def post(db, tags, days_ago=1, published=True, text_missing=0):
    _n[0] += 1
    day = when(days_ago)
    db.execute("INSERT INTO articles (url, site, title, published_at, tags, text_missing, created_at) VALUES (?, 'emtia', 't', ?, ?, ?, ?)",
               (f"https://x/{_n[0]}/", day if published else None, json.dumps(tags, ensure_ascii=False), text_missing, day))
    db.commit()


def stock_row(db, ticker, company="Co", status="candidate"):
    db.execute("INSERT INTO stocks (ticker, company, status, created_at) VALUES (?, ?, ?, 'x')", (ticker, company, status))
    db.commit()


def by_key(r, kind):
    return {e.key: e for e in r.of(kind)}


def test_a_stock_is_counted_once_per_post_even_when_two_tags_point_to_it(db):
    tag(db, "Alibaba", "company", "BABA", 1)
    tag(db, "Alibaba Group", "company", "BABA", 1)
    post(db, ["Alibaba", "Alibaba Group"])
    post(db, ["Alibaba Group"])
    e = by_key(count.count(db, NOW), "stock")["BABA"]
    assert (e.posts_7d, e.posts_30d, e.rank, e.points) == (2, 2, 1, 0)


def test_the_window_is_seven_days_on_the_published_date(db):
    tag(db, "Cummins", "company", "CMI", 1)
    post(db, ["Cummins"], days_ago=1)
    post(db, ["Cummins"], days_ago=6.9)
    post(db, ["Cummins"], days_ago=7.1)                       # outside the 7 days, inside the 30
    post(db, ["Cummins"], days_ago=29)
    post(db, ["Cummins"], days_ago=31)                        # outside both
    e = by_key(count.count(db, NOW), "stock")["CMI"]
    assert (e.posts_7d, e.posts_30d) == (2, 4)


def test_a_post_with_no_published_date_is_dated_by_when_it_was_read(db):
    tag(db, "Cummins", "company", "CMI", 1)
    post(db, ["Cummins"], days_ago=1, published=False)
    assert by_key(count.count(db, NOW), "stock")["CMI"].posts_7d == 1


def test_posts_cut_by_the_paywall_are_counted_because_their_tags_are_on_the_page(db):
    tag(db, "Cummins", "company", "CMI", 1)
    post(db, ["Cummins"], text_missing=1)
    assert by_key(count.count(db, NOW), "stock")["CMI"].posts_7d == 1


def test_us_listed_and_not_us_listed_companies_are_kept_apart(db):
    tag(db, "Cummins", "company", "CMI", 1)
    tag(db, "Zhongkuang Resources", "company", None, 0)
    tag(db, "Tencent", "company", "0700.HK", 0)
    post(db, ["Cummins", "Zhongkuang Resources", "Tencent"])
    r = count.count(db, NOW)
    assert list(by_key(r, "stock")) == ["CMI"]
    assert set(by_key(r, "non_us")) == {"Zhongkuang Resources", "0700.HK"}


def test_commodities_and_sectors_are_counted_from_their_own_tags_only(db):
    tag(db, "Bakır", "commodity", "copper")
    tag(db, "Çelik", "commodity", "copper")
    tag(db, "Fosil Enerji", "sector", "Energy")
    tag(db, "Cummins", "company", "CMI", 1)
    post(db, ["Bakır", "Fosil Enerji", "Cummins"])
    post(db, ["Çelik"])
    r = count.count(db, NOW)
    assert by_key(r, "commodity")["copper"].posts_7d == 2
    assert by_key(r, "sector")["Energy"].posts_7d == 1
    assert "Industrials" not in by_key(r, "sector")             # a company tag adds nothing to a sector


def test_region_other_waiting_and_unclassified_tags_are_not_counted_but_noted(db):
    tag(db, "Japonya", "region")
    tag(db, "Rapor Özetleri", "other")
    tag(db, "Standard Oil", "company", None, 1, status="waiting")
    post(db, ["Japonya", "Rapor Özetleri", "Standard Oil", "Yeni Etiket"])
    r = count.count(db, NOW)
    assert r.entries == [] and (r.waiting_tags, r.unclassified_tags, r.posts_in_window) == (1, 1, 1)


def test_a_stock_with_a_card_is_stored_without_rank_and_does_not_enter_the_ranking(db):
    tag(db, "Coca-Cola", "company", "KO", 1)
    tag(db, "Cummins", "company", "CMI", 1)
    stock_row(db, "KO", "Coca-Cola Co", "watching")
    for _ in range(7):
        post(db, ["Coca-Cola"])
    post(db, ["Cummins"])
    r = count.count(db, NOW)
    ko = by_key(r, "stock")["KO"]
    assert (ko.has_card, ko.rank, ko.points, ko.label) == (True, None, None, "Coca-Cola Co")
    assert by_key(r, "stock")["CMI"].rank == 1                  # not rank 2: KO is outside the ranking
    text = block.render(r)
    assert "Stocks with a card mentioned a lot: KO (7)" in text and "1. CMI" in text


def test_a_stock_with_a_card_below_the_bar_is_not_in_the_note(db):
    tag(db, "Coca-Cola", "company", "KO", 1)
    stock_row(db, "KO")
    for _ in range(5):
        post(db, ["Coca-Cola"])
    assert "mentioned a lot" not in block.render(count.count(db, NOW))


@pytest.mark.parametrize("posts, points", [(1, 0), (2, 0), (3, 1), (5, 1), (6, 2), (40, 2)])
def test_mentions_points(posts, points):
    assert count.mentions_points(posts) == points


def test_order_is_seven_day_posts_then_thirty_day_posts_then_ticker(db):
    for name, tk in (("Alpha", "AAA"), ("Bravo", "BBB"), ("Charlie", "CCC"), ("Delta", "DDD")):
        tag(db, name, "company", tk, 1)
    for _ in range(3):
        post(db, ["Charlie"])
    for _ in range(2):
        post(db, ["Alpha"])
        post(db, ["Bravo"])
        post(db, ["Delta"])
    post(db, ["Delta"], days_ago=20)                              # more history: ahead of the others on a tie
    order = [(e.key, e.rank) for e in count.count(db, NOW).of("stock")]
    assert order == [("CCC", 1), ("DDD", 2), ("AAA", 3), ("BBB", 4)]


def test_the_label_is_the_commonest_tag_name_when_there_is_no_stock_row(db):
    tag(db, "Alibaba", "company", "BABA", 1)
    tag(db, "Alibaba Group", "company", "BABA", 1)
    post(db, ["Alibaba Group"])
    post(db, ["Alibaba Group"])
    post(db, ["Alibaba"])
    assert by_key(count.count(db, NOW), "stock")["BABA"].label == "Alibaba Group"


def test_a_run_is_stored_and_a_second_run_adds_rows_without_deleting(db):
    tag(db, "Cummins", "company", "CMI", 1)
    post(db, ["Cummins"])
    count.count(db, NOW)
    count.count(db, NOW + timedelta(hours=1))
    assert db.execute("SELECT count(*), count(DISTINCT run_at) FROM counts").fetchone() == (2, 2)
    last = count.latest(db)
    assert last.run_at == clock.utc_iso(NOW + timedelta(hours=1)) and by_key(last, "stock")["CMI"].points == 0


def test_write_false_stores_nothing(db):
    tag(db, "Cummins", "company", "CMI", 1)
    post(db, ["Cummins"])
    count.count(db, NOW, write=False)
    assert db.execute("SELECT count(*) FROM counts").fetchone()[0] == 0 and count.latest(db) is None


def test_the_ranking_text_shows_the_top_ten_and_the_other_lists(db):
    for i in range(12):
        tag(db, f"Co{i:02d}", "company", f"T{i:02d}", 1)
        for _ in range(12 - i):
            post(db, [f"Co{i:02d}"])
    tag(db, "Zhongkuang", "company", None, 0)
    tag(db, "Bakır", "commodity", "copper")
    tag(db, "Fosil Enerji", "sector", "Energy")
    post(db, ["Zhongkuang", "Bakır", "Fosil Enerji"])
    text = block.render(count.count(db, NOW))
    assert text.startswith("COUNTER · last 7 days (to 2026-10-12)")
    assert "US stocks to score (top 10 of 12):" in text and "10. T09" in text and "11. T10" not in text
    assert "1. T00 Co00 — 12 posts (30 days: 12) · mentions 2/2" in text
    assert "Non-US names mentioned a lot: Zhongkuang (1)" in text
    assert "Commodities: copper 1" in text and "Sectors: Energy 1" in text


def test_an_empty_database_says_so(db):
    text = block.render(count.count(db, NOW))
    assert "No US stock without a card was mentioned." in text and "No post was read in this window yet." in text


def test_the_command_counts_prints_and_shows_the_stored_run(db, env, capsys):
    tag(db, "Cummins", "company", "CMI", 1)
    post(db, ["Cummins"], days_ago=0)
    db.execute("UPDATE articles SET published_at = ?, created_at = ?", (clock.utc_iso(), clock.utc_iso()))
    db.commit()
    assert cli.main([]) == 0
    assert "1. CMI" in capsys.readouterr().out
    assert db.execute("SELECT count(*) FROM counts").fetchone()[0] == 1
    assert cli.main(["--show"]) == 0
    shown = capsys.readouterr().out
    assert "stored run of" in shown and "1. CMI" in shown
    assert cli.main(["--bogus"]) == 2


def test_show_before_any_run(env, capsys):
    from shared import db as dbmod
    dbmod.init()
    assert cli.main(["--show"]) == 0
    assert "has not run yet" in capsys.readouterr().out


def test_a_latest_run_that_found_nothing_is_not_mistaken_for_the_run_before_it(db):
    """Audit 2026-10-14, #5: an empty run writes no rows, so `latest` must not return an older run as if it were the newest."""
    tag(db, "Apple", "company", maps_to="AAPL", us=1)
    post(db, ["Apple"])
    old = count.count(db, now=NOW)
    assert old.of("stock") and count.latest(db).of("stock")
    # a later successful run of the job that stored nothing (no post in the window any more)
    later = clock.utc_iso(NOW + timedelta(days=30))
    db.execute("INSERT INTO runs (job, started_at, ended_at, status) VALUES ('counter', ?, ?, 'ok')", (later, later))
    db.commit()
    got = count.latest(db)
    assert got is not None and got.entries == [] and got.run_at == later


def test_a_post_dated_in_the_future_is_not_counted(db):
    tag(db, "Fortum", "company", "FORTUM.HE", 0)
    post(db, ["Fortum"], days_ago=1)
    post(db, ["Fortum"], days_ago=-30)                     # a wrong date on the page: 30 days ahead
    assert {e.key: e.posts_7d for e in count.count(db, NOW, write=False).of("non_us")} == {"FORTUM.HE": 1}
