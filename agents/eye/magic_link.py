"""Sign in to a Ghost site with the one-time link in its e-mail and keep the login cookie in `.env`, without ever showing it.

    uv run python -m agents.eye.magic_link dragonomi '<the sign-in link from the e-mail>'
    uv run python -m agents.eye.magic_link dragonomi --stdin          (the link on standard input)

Why (roadmap "Morning bulletin" 11, "Yol B"): Ghost has no password. I ask the site for a sign-in link on my phone, do NOT open it,
and send it to Hermes; this opens it once from the Air and writes the cookie it gets into `.env` (`DRAGONOMI_COOKIE`). A link works once, so
what passes through Telegram is worthless afterwards; the long-lived cookie never leaves the Air. Only a link of the site's own
address (`https://<site>/members/?token=…`) is opened, nothing else; redirects are not followed; the token and the cookie are never
printed or put in an error. If the e-mail holds a code instead of a link, this cannot be used (tell Claude).

Afterwards: `python -m agents.eye.session_check dragonomi`, then take the site out of `eye.skip_sites` in settings.yaml.
"""

from __future__ import annotations

import http.client
import re
import sys
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urlsplit

from agents.eye import http as eye_http
from agents.eye import set_cookie
from agents.eye.sites import SITES, Site

USAGE = "usage: python -m agents.eye.magic_link dragonomi '<sign-in link>'   (or --stdin)"
COOKIE_NAMES = ("ghost-members-ssr", "ghost-members-ssr.sig")
TIMEOUT_S = 30


class LinkError(ValueError):
    """Why nothing was done. The message never holds the link, the token or the cookie."""


def target_of(site: Site, link: str) -> tuple[str, str]:
    """(host, path?query) of a sign-in link of this site; anything else is refused before any request."""
    parts = urlsplit(link.strip().strip("<>\"'` \n"))
    host = urlsplit(site.base).hostname
    if parts.scheme != "https" or parts.hostname != host or parts.username or parts.password or parts.port not in (None, 443):
        raise LinkError(f"that is not a link of {host}; nothing was opened")
    if not (parts.path == "/members" or parts.path.startswith("/members/")) or not parse_qs(parts.query).get("token"):
        raise LinkError(f"that is a {host} link but not a sign-in link (it should look like https://{host}/members/?token=…); nothing was opened")
    return host, parts.path + ("?" + parts.query if parts.query else "")


def open_once(host: str, target: str) -> tuple[int, list[tuple[str, str]]]:
    """One GET, no redirect followed. Returns (status, headers). Replaced in tests."""
    conn = http.client.HTTPSConnection(host, timeout=TIMEOUT_S)
    try:
        conn.request("GET", target, headers={"User-Agent": eye_http.USER_AGENT, "Accept": "text/html"})
        response = conn.getresponse()
        response.read(65536)
        return response.status, response.getheaders()
    except (OSError, http.client.HTTPException) as exc:
        raise LinkError(f"{host} could not be reached ({type(exc).__name__}); the link may still be unused") from None
    finally:
        conn.close()


def cookies_from(headers: list[tuple[str, str]]) -> tuple[dict, datetime | None]:
    """The members cookies the site set ({name: value}) and the earliest expiry among them."""
    found, expiry = {}, None
    now = datetime.now(timezone.utc)
    for key, line in headers:
        if key.lower() != "set-cookie":
            continue
        first, *attributes = [x.strip() for x in line.split(";")]
        name, _, value = first.partition("=")
        if name not in COOKIE_NAMES or not value:
            continue
        found[name] = value
        for attribute in attributes:
            low = attribute.lower()
            try:
                if low.startswith("max-age="):
                    moment = now + timedelta(seconds=int(low.split("=", 1)[1]))
                elif low.startswith("expires="):
                    moment = parsedate_to_datetime(attribute.split("=", 1)[1])
                else:
                    continue
            except (ValueError, TypeError):
                continue
            expiry = moment if expiry is None else min(expiry, moment)
    return found, expiry


def sign_in(site: Site, link: str) -> tuple[str, datetime | None]:
    """Opens the link once. Returns (the cookie header value, its expiry). Raises LinkError."""
    host, target = target_of(site, link)
    status, headers = open_once(host, target)
    location = next((v for k, v in headers if k.lower() == "location"), "")
    if "success=false" in location:
        raise LinkError("the site refused the link: it was already used or is too old. Ask the site for a new sign-in link and open nothing")
    cookies, expiry = cookies_from(headers)
    if "ghost-members-ssr" not in cookies:
        raise LinkError(f"the site answered HTTP {status} but did not sign in (no members cookie). The link may be used or wrong; ask for a new one")
    return "; ".join(f"{n}={cookies[n]}" for n in COOKIE_NAMES if n in cookies), expiry


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    use_stdin = "--stdin" in argv
    args = [a for a in argv if a != "--stdin"]
    if len(args) != (1 if use_stdin else 2) or args[0] not in SITES:
        print(USAGE)
        return 2
    site = SITES[args[0]]
    link = sys.stdin.read() if use_stdin else args[1]
    try:
        value, expiry = sign_in(site, link)
        dropped = set_cookie.save(site.cookie_env, value)
    except (LinkError, ValueError) as exc:
        print(f"SIGN-IN · failed\n{exc}")
        return 1
    until = f"valid until {expiry.astimezone(timezone.utc):%Y-%m-%d} (the site's own date)" if expiry else "the site gave no expiry date"
    print(f"SIGN-IN · {site.name}\n{site.cookie_env} saved ({len(value)} characters), {until}. Broken lines removed from .env: {dropped}. "
          f"The old file is kept as .env.bak.\nNext: python -m agents.eye.session_check {site.key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
