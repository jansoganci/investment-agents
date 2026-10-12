import json

import pytest

from agents.eye import http, run
from agents.eye.sites import SITES
from shared import db as dbmod

from .helpers import DRAGONOMI_FULL, EMTIA_FULL, EMTIA_GATED, page

EM, DR = SITES["emtia"], SITES["dragonomi"]
COOKIES = {"emtia": "e=1", "dragonomi": "d=2"}


def sitemap(site, names, lastmods=None):
    lastmods = lastmods or {}
    rows = "".join(f"<url><loc>{site.base}/{n}/</loc><lastmod>{lastmods.get(n, '2026-10-11T00:00:00Z')}</lastmod></url>" for n in names)
    return f'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>'


class Web:
    """A fake site: sitemaps and pages by address; records every request."""

    def __init__(self):
        self.pages, self.calls = {}, []

    def set_sitemap(self, site, names, lastmods=None):
        self.pages[site.posts_sitemap] = sitemap(site, names, lastmods)

    def __call__(self, url, cookie=None, timeout=30):
        self.calls.append((url, cookie))
        what = self.pages.get(url, 404)
        if isinstance(what, Exception):
            raise what
        if isinstance(what, int):
            return http.Response(url, what, [], b"")
        return http.Response(url, 200, [], what.encode())


@pytest.fixture
def web():
    return Web()


def go(conn, web, **kw):
    sleeps = kw.pop("sleeps", [])
    return run.run_pass(conn, cookies=COOKIES, fetch=web, sleep=sleeps.append, pause=lambda a, b: a, **kw)


def first_run(conn, web, em=("old-1", "old-2"), dr=("old-3",)):
    web.set_sitemap(EM, em)
    web.set_sitemap(DR, dr)
    return go(conn, web)


def how(conn):
    return dict(conn.execute("SELECT url, how FROM eye_seen").fetchall())


def test_first_run_is_a_baseline_it_reads_no_post_and_says_so(db, web):
    result = first_run(db, web)
    assert [c[0] for c in web.calls] == [EM.posts_sitemap, DR.posts_sitemap]
    assert all(cookie is None for _, cookie in web.calls)
    assert set(how(db).values()) == {"baseline"} and len(how(db)) == 3
    assert db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0
    assert "first run — 2 addresses" in result.message() and "first run — 1 addresses" in result.message()


def test_a_quiet_pass_prints_nothing_and_asks_only_the_sitemaps(db, web):
    first_run(db, web)
    web.calls.clear()
    result = go(db, web)
    assert result.message() is None and len(web.calls) == 2


def test_a_new_post_is_read_with_the_cookie_and_saved(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "fresh"])
    web.pages[f"{EM.base}/fresh/"] = EMTIA_FULL
    web.calls.clear()
    result = go(db, web)
    assert (f"{EM.base}/fresh/", "e=1") in web.calls
    cur = db.execute("SELECT site, title, published_at, tags, full_text, read_deep, text_missing, sentence FROM articles")
    row = dict(zip([d[0] for d in cur.description], cur.fetchone()))
    assert row["site"] == "emtia" and row["title"].startswith("Soya")
    assert row["published_at"] == "2026-10-11T05:48:48Z"
    assert json.loads(row["tags"]) == ["Petrol", "Asya"]
    assert "Soya fasulyesi vadeli" in row["full_text"]
    assert (row["read_deep"], row["text_missing"], row["sentence"]) == (0, 0, None)
    assert how(db)[f"{EM.base}/fresh/"] == "read" and result.message() is None


def test_a_page_cut_by_the_paywall_is_text_missing_and_never_asked_again(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "cut"])
    web.pages[f"{EM.base}/cut/"] = EMTIA_GATED
    result = go(db, web)
    assert db.execute("SELECT text_missing FROM articles").fetchone()[0] == 1
    assert how(db)[f"{EM.base}/cut/"] == "text_missing"
    assert "1 page(s) were cut by the paywall" in result.message()
    web.calls.clear()
    go(db, web)
    assert [c[0] for c in web.calls] == [EM.posts_sitemap, DR.posts_sitemap]       # not tried again


def test_a_glossary_post_is_seen_but_not_saved(db, web):
    first_run(db, web)
    web.set_sitemap(DR, ["old-3", "sozluk"])
    web.pages[f"{DR.base}/sozluk/"] = page("<div class='content'><p>x</p></div>", tags=("Yatırım Sözlüğü",))
    go(db, web)
    assert db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0
    assert how(db)[f"{DR.base}/sozluk/"] == "glossary"


def test_a_removed_post_is_marked_gone(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "vanished"])
    go(db, web)                                   # the page answers 404
    assert how(db)[f"{EM.base}/vanished/"] == "gone"


def test_more_than_200_new_addresses_read_nothing_and_stop(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2"] + [f"n{i}" for i in range(201)])
    web.calls.clear()
    with pytest.raises(run.PassStopped, match="Unusual number of new posts: 201"):
        go(db, web)
    assert [c[0] for c in web.calls] == [EM.posts_sitemap, DR.posts_sitemap]
    assert len(how(db)) == 3


def test_accept_many_goes_on_but_only_80_pages_a_pass_and_the_rest_wait(db, web):
    first_run(db, web)
    names = [f"n{i:03d}" for i in range(201)]
    web.set_sitemap(EM, ["old-1", "old-2"] + names)
    for n in names:
        web.pages[f"{EM.base}/{n}/"] = EMTIA_FULL
    web.calls.clear()
    go(db, web, accept_many=True)
    assert db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 80
    assert db.execute("SELECT COUNT(*) FROM eye_seen WHERE how = 'read'").fetchone()[0] == 80
    web.calls.clear()
    go(db, web, guard=200)                                          # 121 still wait: below the limit, the next 80 are read
    assert db.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 160


def test_the_two_sites_are_taken_in_turn_oldest_first(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "e-new", "e-old"], {"e-old": "2026-10-10T00:00:00Z", "e-new": "2026-10-11T09:00:00Z"})
    web.set_sitemap(DR, ["old-3", "d-1", "d-2"], {"d-1": "2026-10-11T01:00:00Z", "d-2": "2026-10-11T02:00:00Z"})
    for n in ("e-new", "e-old"):
        web.pages[f"{EM.base}/{n}/"] = EMTIA_FULL
    for n in ("d-1", "d-2"):
        web.pages[f"{DR.base}/{n}/"] = DRAGONOMI_FULL
    web.calls.clear()
    result = go(db, web, cap=3)
    asked = [c[0].rsplit("/", 2)[-2] for c in web.calls[2:]]
    assert asked == ["e-old", "d-1", "e-new"]
    assert result.tally["dragonomi"].waiting == 1


def test_a_block_stops_the_pass_at_once_and_keeps_what_was_read(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "a", "b", "c"], {"a": "2026-10-11T01:00:00Z", "b": "2026-10-11T02:00:00Z", "c": "2026-10-11T03:00:00Z"})
    web.pages[f"{EM.base}/a/"] = EMTIA_FULL
    web.pages[f"{EM.base}/b/"] = http.Blocked("429")
    web.pages[f"{EM.base}/c/"] = EMTIA_FULL
    web.calls.clear()
    with pytest.raises(run.PassStopped, match="blocked us"):
        go(db, web)
    assert f"{EM.base}/c/" not in [c[0] for c in web.calls]
    assert how(db)[f"{EM.base}/a/"] == "read" and f"{EM.base}/b/" not in how(db)


def test_three_pages_in_a_row_without_a_body_stop_the_pass_and_are_not_recorded(db, web):
    first_run(db, web)
    names = ["a", "b", "c", "d"]
    web.set_sitemap(EM, ["old-1", "old-2"] + names)
    for n in names:
        web.pages[f"{EM.base}/{n}/"] = "<html><body><p>new layout</p></body></html>"
    with pytest.raises(run.PassStopped, match="3 pages in a row failed"):
        go(db, web)
    assert not any(u.rsplit("/", 2)[-2] in names for u in how(db))


def test_a_good_page_resets_the_count_of_failures(db, web):
    first_run(db, web)
    names = ["a", "b", "c", "d", "e"]
    web.set_sitemap(EM, ["old-1", "old-2"] + names, {n: f"2026-10-11T0{i}:00:00Z" for i, n in enumerate(names)})
    for n in names:
        web.pages[f"{EM.base}/{n}/"] = "<html></html>"
    web.pages[f"{EM.base}/c/"] = EMTIA_FULL
    result = go(db, web)                                   # a, b fail, c is fine, d, e fail: never 3 in a row
    assert result.tally["emtia"].failed == 4 and result.tally["emtia"].read == 1


def test_a_site_without_a_cookie_is_not_read_and_says_so(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "fresh"])
    web.calls.clear()
    result = run.run_pass(db, cookies={"emtia": "", "dragonomi": "d=2"}, fetch=web, sleep=lambda s: None, pause=lambda a, b: a)
    assert [c[0] for c in web.calls] == [EM.posts_sitemap, DR.posts_sitemap]
    assert "EMTIA_COOKIE is not set" in result.message()
    assert f"{EM.base}/fresh/" not in how(db)


def test_it_waits_between_requests_but_not_before_the_first(db, web):
    sleeps = []
    first_run_sleeps = []
    web.set_sitemap(EM, ["old-1"])
    web.set_sitemap(DR, ["old-3"])
    run.run_pass(db, cookies=COOKIES, fetch=web, sleep=first_run_sleeps.append, pause=lambda a, b: 25)
    assert first_run_sleeps == [25]                         # two sitemap requests, one pause between them
    web.set_sitemap(EM, ["old-1", "n"])
    web.pages[f"{EM.base}/n/"] = EMTIA_FULL
    run.run_pass(db, cookies=COOKIES, fetch=web, sleep=sleeps.append, pause=lambda a, b: 25)
    assert sleeps == [25, 25]                               # sitemap, sitemap, post


def test_a_sitemap_that_is_empty_or_broken_is_an_error_not_a_baseline(db, web):
    web.pages[EM.posts_sitemap] = "<urlset></urlset>"
    web.pages[DR.posts_sitemap] = sitemap(DR, ["x"])
    with pytest.raises(run.PassStopped, match="sitemap could not be read"):
        go(db, web)
    assert how(db) == {}


def test_a_cross_host_address_in_the_sitemap_is_never_fetched(db, web):
    web.set_sitemap(EM, ["old-1"])
    web.set_sitemap(DR, ["old-3"])
    go(db, web)
    web.pages[EM.posts_sitemap] = (
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{EM.base}/old-1/</loc></url><url><loc>https://evil.example/steal/</loc></url></urlset>"
    )
    web.calls.clear()
    go(db, web)
    assert "https://evil.example/steal/" not in [c[0] for c in web.calls]


def test_the_database_is_at_the_latest_version_with_the_new_table(db):
    assert dbmod.version(db) >= 6
    assert db.execute("SELECT name FROM sqlite_master WHERE name='eye_seen'").fetchone()


def _gated(db, web, names):
    web.set_sitemap(EM, ["old-1", "old-2", *names])
    for n in names:
        web.pages[f"{EM.base}/{n}/"] = EMTIA_GATED
    return go(db, web)


def test_five_cut_pages_in_a_row_say_the_cookie_has_probably_expired(db, web):
    first_run(db, web)
    result = _gated(db, web, ["a", "b", "c", "d", "e"])
    assert "the last 5 pages in a row were cut by the paywall" in result.message()
    assert "set_cookie emtia" in result.message()


def test_four_cut_pages_or_a_good_page_among_them_do_not_say_it(db, web):
    first_run(db, web)
    assert "probably expired" not in _gated(db, web, ["a", "b", "c", "d"]).message()
    web.set_sitemap(EM, ["old-1", "old-2", "a", "b", "c", "d", "ok"])
    web.pages[f"{EM.base}/ok/"] = EMTIA_FULL
    go(db, web)                                              # a good page is read after the four cut ones
    web.set_sitemap(EM, ["old-1", "old-2", "a", "b", "c", "d", "ok", "e"])
    web.pages[f"{EM.base}/e/"] = EMTIA_GATED
    result = go(db, web)                                     # one more cut page: the newest five are not all cut
    assert "probably expired" not in (result.message() or "")


def test_no_cookie_no_warning(db, web):
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "a", "b", "c", "d", "e"])
    for n in "abcde":
        web.pages[f"{EM.base}/{n}/"] = EMTIA_GATED
    result = run.run_pass(db, cookies={"emtia": "", "dragonomi": ""}, fetch=web, sleep=lambda s: None, pause=lambda a, b: a)
    assert "probably expired" not in (result.message() or "")
