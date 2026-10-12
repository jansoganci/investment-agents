"""Does my stored login give the full text?  (Run on the main Mac, in your own terminal — the cookie never leaves it.)

    uv run python -m agents.eye.session_check emtia            [--url <post address>]
    uv run python -m agents.eye.session_check dragonomi        [--url <post address>]

It takes the newest post of the site's sitemap (or the address you give), asks for it twice — once without the cookie, once with
it — and prints what each page shows: status, size, whether the page is cut, which body selector matched, how many characters of
text, the first 200. Three requests per site, six seconds apart. The cookie value is never printed.

How to get the cookie: log in to the site in your browser → open any post → developer tools → Network → click the post's
request → Request Headers → copy the whole value of `cookie:` → `uv run python -m agents.eye.set_cookie emtia` (or `dragonomi`) puts
it in `.env`. Never commit it, never send it to Telegram or to Hermes."""

from __future__ import annotations

import os
import sys
import time
import xml.etree.ElementTree as ET

from agents.eye import http
from agents.eye.extract import Post, is_glossary, parse_post
from agents.eye.sites import SITES, Site
from shared import config  # noqa: F401  (loads .env)

PAUSE_S = 6
USAGE = "usage: python -m agents.eye.session_check emtia|dragonomi [--url <post address>]"


def newest_post(site: Site) -> str:
    """The post with the latest lastmod in the sitemap (one request, no cookie)."""
    response = http.fetch(site.posts_sitemap, timeout=60)
    root = ET.fromstring(response.body)
    best = None
    for node in root:
        loc = lastmod = None
        for child in node:
            name = child.tag.rsplit("}", 1)[-1]
            if name == "loc":
                loc = (child.text or "").strip()
            elif name == "lastmod":
                lastmod = (child.text or "").strip()
        if loc and "/tag/" not in loc and (best is None or (lastmod or "") > best[0]):
            best = (lastmod or "", loc)
    if best is None:
        raise http.FetchError(f"no post found in {site.posts_sitemap}")
    return best[1]


def show(label: str, response: http.Response, post: Post, site: Site) -> list[str]:
    lines = [
        f"--- {label} ---",
        f"HTTP {response.status} · {len(response.body):,} bytes",
        f"title: {post.title}",
        f"published: {post.published_at}",
        f"tags ({len(post.tags)}): {', '.join(post.tags) or '-'}",
        f"gated (a log-in / subscribe block is on the page): {post.gated}",
        f"body found by: {post.body_selector} (matches: {post.body_matches})",
        f"text: {len(post.text):,} characters" + (" · glossary post" if is_glossary(post, site) else ""),
        f"first 200: {post.text[:200]!r}",
    ]
    notes = response.cookie_notes()
    if notes:
        lines.append("cookies the site set: " + "; ".join(notes))
    return lines


def verdict(without: Post, with_cookie: Post) -> str:
    if with_cookie.gated:
        return "NOT OK — with the cookie the page is still cut. The cookie is wrong or expired (or the site needs another way in)."
    if with_cookie.body_selector is None:
        return "NOT OK — no body found with the cookie. Send me the lines above; the selector needs a look."
    if len(with_cookie.text) <= len(without.text):
        return "NOT OK — the cookie gave no more text than a visitor gets."
    note = " (short: check the first 200 characters by eye)" if len(with_cookie.text) < 300 else ""
    return f"OK — with the cookie the page is whole: {len(with_cookie.text):,} characters against {len(without.text):,}.{note}"


def main(argv: list[str] | None = None, sleep=time.sleep) -> int:
    argv = sys.argv[1:] if argv is None else argv
    url = None
    if "--url" in argv:
        i = argv.index("--url")
        if i + 1 >= len(argv):
            print(USAGE)
            return 2
        url = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    if len(argv) != 1 or argv[0] not in SITES:
        print(USAGE)
        return 2
    site = SITES[argv[0]]
    cookie = os.environ.get(site.cookie_env, "").strip()
    if not cookie:
        print(f"{site.cookie_env} is not set in .env. How to get it: see the top of agents/eye/session_check.py.")
        return 2
    try:
        if url is None:
            url = newest_post(site)
            sleep(PAUSE_S)
        elif not url.startswith(site.base + "/"):
            print(f"The address must start with {site.base}/ — the cookie is only sent to that site.")
            return 2
        print(f"{site.name}: {url}")
        plain = http.fetch(url)
        without = parse_post(plain.text, site)
        sleep(PAUSE_S)
        logged = http.fetch(url, cookie=cookie)
        with_cookie = parse_post(logged.text, site)
    except http.Blocked as error:
        print(f"STOPPED — the site blocked us: {error}. Nothing more was asked. Wait and tell me.")
        return 1
    except (http.FetchError, ET.ParseError) as error:
        print(f"Failed: {error}")
        return 1
    print("\n".join(show("without the cookie", plain, without, site)))
    print("\n".join(show("with the cookie", logged, with_cookie, site)))
    print()
    print(verdict(without, with_cookie))
    return 0


if __name__ == "__main__":
    sys.exit(main())
