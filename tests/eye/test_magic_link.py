"""agents/eye/magic_link: the one-time sign-in link of a Ghost site → the login cookie in `.env`, with no token or cookie ever printed."""

import io
from datetime import datetime, timezone

import pytest

from agents.eye import magic_link, set_cookie
from agents.eye.sites import SITES

SITE = SITES["dragonomi"]
TOKEN = "tkn-1a2b3c4d5e6f7a8b9c0d"
LINK = f"https://www.dragonomi.com/members/?token={TOKEN}&action=signin&r=https%3A%2F%2Fwww.dragonomi.com%2F"
SSR, SIG = "s%3Amember%40mail.com.AbCdEf", "XyZ123sig"
SIGNED_IN = [("Location", "/?action=signin&success=true"),
             ("Set-Cookie", f"ghost-members-ssr={SSR}; Max-Age=15552000; Path=/; HttpOnly; SameSite=Lax"),
             ("Set-Cookie", f"ghost-members-ssr.sig={SIG}; Max-Age=15552000; Path=/; HttpOnly"),
             ("Set-Cookie", "_other=1; Path=/")]


def fake_open(monkeypatch, status=302, headers=SIGNED_IN):
    calls = []
    monkeypatch.setattr(magic_link, "open_once", lambda host, target: (calls.append((host, target)) or (status, headers)))
    return calls


@pytest.mark.parametrize("link", [LINK, f"<{LINK}>", f"  '{LINK}'\n", f'"{LINK}"'])
def test_a_link_of_the_site_is_accepted_however_it_was_pasted(link):
    assert magic_link.target_of(SITE, link) == ("www.dragonomi.com", f"/members/?token={TOKEN}&action=signin&r=https%3A%2F%2Fwww.dragonomi.com%2F")


@pytest.mark.parametrize("link", [
    f"http://www.dragonomi.com/members/?token={TOKEN}",                     # not https
    f"https://evil.example/members/?token={TOKEN}",                         # another site
    f"https://www.dragonomi.com.evil.example/members/?token={TOKEN}",       # a look-alike host
    f"https://www.dragonomi.com@evil.example/members/?token={TOKEN}",       # the user-info trick
    "https://www.dragonomi.com/some-post/",                                 # the site's, but not a sign-in link
    "https://www.dragonomi.com/members/?action=signin",                     # no token
    "not a link"])
def test_anything_else_is_refused_before_a_request(link):
    with pytest.raises(magic_link.LinkError) as caught:
        magic_link.target_of(SITE, link)
    assert TOKEN not in str(caught.value)


def test_signing_in_returns_the_members_cookies_and_the_earliest_expiry(monkeypatch):
    calls = fake_open(monkeypatch)
    value, expiry = magic_link.sign_in(SITE, LINK)
    assert value == f"ghost-members-ssr={SSR}; ghost-members-ssr.sig={SIG}"            # the other cookie is left out
    assert calls == [("www.dragonomi.com", f"/members/?token={TOKEN}&action=signin&r=https%3A%2F%2Fwww.dragonomi.com%2F")]   # opened once
    assert 150 < (expiry - datetime.now(timezone.utc)).days < 200


def test_an_expires_date_is_read_too_and_the_earlier_one_counts():
    headers = [("set-cookie", "ghost-members-ssr=a; Expires=Wed, 21 Oct 2026 07:28:00 GMT; Path=/"),
               ("Set-Cookie", "ghost-members-ssr.sig=b; Expires=Thu, 22 Oct 2026 07:28:00 GMT; Path=/")]
    cookies, expiry = magic_link.cookies_from(headers)
    assert cookies == {"ghost-members-ssr": "a", "ghost-members-ssr.sig": "b"}
    assert expiry == datetime(2026, 10, 21, 7, 28, tzinfo=timezone.utc)


def test_a_used_link_or_a_page_without_cookies_is_a_plain_error_without_the_token(monkeypatch):
    fake_open(monkeypatch, headers=[("Location", "/signin/?action=signin&success=false")])
    with pytest.raises(magic_link.LinkError, match="already used or is too old") as caught:
        magic_link.sign_in(SITE, LINK)
    assert TOKEN not in str(caught.value)
    fake_open(monkeypatch, status=200, headers=[("Content-Type", "text/html")])
    with pytest.raises(magic_link.LinkError, match="did not sign in"):
        magic_link.sign_in(SITE, LINK)


def test_an_unreachable_site_says_the_link_may_still_be_unused(monkeypatch):
    class Down:
        def __init__(self, *a, **k):
            pass

        def request(self, *a, **k):
            raise OSError("boom " + TOKEN)

        def close(self):
            pass
    monkeypatch.setattr(magic_link.http.client, "HTTPSConnection", Down)
    with pytest.raises(magic_link.LinkError, match="may still be unused") as caught:
        magic_link.open_once("www.dragonomi.com", f"/members/?token={TOKEN}")
    assert TOKEN not in str(caught.value)


def test_main_writes_the_cookie_into_env_and_prints_neither_it_nor_the_token(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".env"
    env.write_text("SEC_UA=me\nDRAGONOMI_COOKIE=''\n")
    monkeypatch.setattr(set_cookie, "env_path", lambda: env)
    fake_open(monkeypatch)
    assert magic_link.main(["dragonomi", LINK]) == 0
    assert env.read_text() == f"SEC_UA=me\nDRAGONOMI_COOKIE='ghost-members-ssr={SSR}; ghost-members-ssr.sig={SIG}'\n"
    assert (tmp_path / ".env.bak").read_text() == "SEC_UA=me\nDRAGONOMI_COOKIE=''\n"
    out = capsys.readouterr().out
    assert out.startswith("SIGN-IN · Dragonomi\nDRAGONOMI_COOKIE saved (") and "valid until 2027-" in out
    for secret in (TOKEN, SSR, SIG):
        assert secret not in out
    assert "session_check dragonomi" in out


def test_main_takes_the_link_on_stdin_and_refuses_a_wrong_one_without_a_request(tmp_path, monkeypatch, capsys):
    env = tmp_path / ".env"
    env.write_text("SEC_UA=me\n")
    monkeypatch.setattr(set_cookie, "env_path", lambda: env)
    calls = fake_open(monkeypatch)
    monkeypatch.setattr("sys.stdin", io.StringIO(f"https://evil.example/members/?token={TOKEN}\n"))
    assert magic_link.main(["dragonomi", "--stdin"]) == 1
    assert calls == [] and env.read_text() == "SEC_UA=me\n"
    out = capsys.readouterr().out
    assert out.startswith("SIGN-IN · failed") and TOKEN not in out
    assert magic_link.main(["nowhere", LINK]) == 2 and magic_link.main(["dragonomi"]) == 2
