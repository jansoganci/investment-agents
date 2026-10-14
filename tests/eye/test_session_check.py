import pytest

from agents.eye import http, session_check
from agents.eye.sites import SITES

from .helpers import DRAGONOMI_FULL, DRAGONOMI_TEASER, EMTIA_FULL, EMTIA_GATED

SITEMAP = b"""<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://www.emtiadefteri.com/old/</loc><lastmod>2026-10-01T00:00:00Z</lastmod></url>
<url><loc>https://www.emtiadefteri.com/newest/</loc><lastmod>2026-10-11T05:48:48Z</lastmod></url>
<url><loc>https://www.emtiadefteri.com/middle/</loc><lastmod>2026-10-05T00:00:00Z</lastmod></url></urlset>"""

COOKIE = "ghost-members-ssr=TOPSECRETVALUE; other=1"


def reply(body, status=200):
    return http.Response("u", status, [("Set-Cookie", "ghost-members-ssr=TOPSECRETVALUE; Max-Age=15552000")], body.encode() if isinstance(body, str) else body)


def run(monkeypatch, capsys, args, plain, logged, site_cookie=COOKIE):
    calls = []

    def fake(url, cookie=None, timeout=30):
        calls.append((url, cookie))
        if url.endswith("sitemap-posts.xml"):
            return reply(SITEMAP)
        return reply(logged if cookie else plain)

    monkeypatch.setattr(http, "fetch", fake)
    monkeypatch.setenv("EMTIA_COOKIE", site_cookie)
    monkeypatch.setenv("DRAGONOMI_COOKIE", site_cookie)
    code = session_check.main(args, sleep=lambda s: None)
    return code, capsys.readouterr().out, calls


def test_cookie_that_opens_the_page_is_ok_and_never_printed(monkeypatch, capsys):
    code, out, calls = run(monkeypatch, capsys, ["emtia"], EMTIA_GATED, EMTIA_FULL)
    assert code == 0
    assert "OK — with the cookie the page is whole" in out
    assert "TOPSECRETVALUE" not in out
    assert calls == [("https://www.emtiadefteri.com/sitemap-posts.xml", None),
                     ("https://www.emtiadefteri.com/newest/", None),
                     ("https://www.emtiadefteri.com/newest/", COOKIE)]        # newest by lastmod; cookie only on the post
    assert "ghost-members-ssr (Max-Age=15552000)" in out


def test_cookie_that_still_meets_the_gate_is_not_ok(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, ["emtia"], EMTIA_GATED, EMTIA_GATED)
    assert code == 0 and "NOT OK — with the cookie the page is still cut" in out


def test_dragonomi_teaser_against_full_page_is_ok(monkeypatch, capsys):
    url = "https://www.dragonomi.com/some-post/"
    code, out, calls = run(monkeypatch, capsys, ["dragonomi", "--url", url], DRAGONOMI_TEASER, DRAGONOMI_FULL)
    assert code == 0 and "OK" in out
    assert [c[0] for c in calls] == [url, url]                                 # no sitemap when an address is given


def test_a_full_page_that_is_not_longer_than_the_visitor_page_is_not_ok(monkeypatch, capsys):
    code, out, _ = run(monkeypatch, capsys, ["emtia"], EMTIA_FULL, EMTIA_FULL)
    assert "NOT OK — the cookie gave no more text" in out


def test_missing_cookie_asks_for_it_and_asks_nothing_of_the_site(monkeypatch, capsys):
    code, out, calls = run(monkeypatch, capsys, ["emtia"], EMTIA_GATED, EMTIA_FULL, site_cookie="")
    assert code == 2 and "EMTIA_COOKIE is not set" in out and calls == []


def test_an_address_of_another_site_is_refused_so_the_cookie_cannot_leak(monkeypatch, capsys):
    code, out, calls = run(monkeypatch, capsys, ["emtia", "--url", "https://evil.example/x/"], EMTIA_GATED, EMTIA_FULL)
    assert code == 2 and calls == []


def test_a_block_stops_at_once(monkeypatch, capsys):
    def blocked(url, cookie=None, timeout=30):
        raise http.Blocked(f"{url} answered 429")

    monkeypatch.setattr(http, "fetch", blocked)
    monkeypatch.setenv("EMTIA_COOKIE", COOKIE)
    assert session_check.main(["emtia", "--url", "https://www.emtiadefteri.com/x/"], sleep=lambda s: None) == 1
    assert "STOPPED" in capsys.readouterr().out


@pytest.mark.parametrize("args", [[], ["unknown"], ["emtia", "--url"]])
def test_bad_usage_prints_usage(args, capsys):
    assert session_check.main(args, sleep=lambda s: None) == 2
    assert "usage:" in capsys.readouterr().out


def test_the_newest_post_is_taken_only_from_the_sites_own_host(monkeypatch):
    """Audit 2026-10-14, #13: a foreign address in a sitemap must never be fetched with the cookie."""
    sitemap = (b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               b'<url><loc>https://evil.example/steal/</loc><lastmod>2030-01-01T00:00:00Z</lastmod></url>'
               b'<url><loc>https://www.emtiadefteri.com/mine/</loc><lastmod>2026-10-11T05:48:48Z</lastmod></url></urlset>')
    monkeypatch.setattr(http, "fetch", lambda url, cookie=None, timeout=30: reply(sitemap))
    assert session_check.newest_post(SITES["emtia"]) == "https://www.emtiadefteri.com/mine/"
