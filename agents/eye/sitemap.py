"""A Ghost posts sitemap → the post addresses. Only addresses on the site's own host are kept: the login cookie is sent to every
address we fetch, so an address pointing elsewhere is dropped here, before anything is asked."""

from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET
from typing import NamedTuple

from agents.eye.sites import Site


class Entry(NamedTuple):
    url: str
    lastmod: str


def _host(url: str) -> str:
    return (urllib.parse.urlparse(url).hostname or "").removeprefix("www.")


def posts(site: Site, body: bytes) -> list[Entry]:
    """The posts of the sitemap, in its order. Raises ValueError if the file is not a sitemap or holds no post of this site."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError as error:
        raise ValueError(f"{site.posts_sitemap} is not a sitemap: {error}") from None
    found: list[Entry] = []
    for node in root:
        loc = lastmod = ""
        for child in node:
            name = child.tag.rsplit("}", 1)[-1]
            if name == "loc":
                loc = (child.text or "").strip()
            elif name == "lastmod":
                lastmod = (child.text or "").strip()
        loc = urllib.parse.urldefrag(loc)[0]
        parts = urllib.parse.urlparse(loc)
        if parts.scheme == "https" and _host(loc) == _host(site.base):
            found.append(Entry(loc, lastmod))
    if not found:
        raise ValueError(f"{site.posts_sitemap} holds no post of {site.name}")
    return found
