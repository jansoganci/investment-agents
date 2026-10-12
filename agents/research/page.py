"""A source page of a news event, as plain text, so the quote the model gave can be looked for in it (code check first, then the
auditor — roadmap, "AI auditor" card 4). A plain GET, no login. The address comes from a web search, so it is never fetched when it
leads to this machine or a private network."""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request

from shared.sec.filing import html_to_text

USER_AGENT = "investment-agents-research (personal use)"


class PageError(RuntimeError):
    """The page could not be fetched or is not a text page."""


def public_address(url: str) -> bool:
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except OSError:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            return False
    return bool(infos)


class _Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not public_address(newurl):
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_Redirect)


def fetch_text(url: str, max_bytes: int = 2_000_000, timeout: float = 20) -> str:
    if not public_address(url):
        raise PageError("the address is not a public web address")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"})
    try:
        with _opener.open(request, timeout=timeout) as answer:
            kind = (answer.headers.get("Content-Type") or "").lower()
            if "html" not in kind and "text" not in kind:
                raise PageError(f"not a text page ({kind or 'unknown type'})")
            body = answer.read(max_bytes)
            charset = answer.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as error:
        raise PageError(f"HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise PageError(str(getattr(error, "reason", error))) from None
    text = body.decode(charset, errors="replace")
    return html_to_text(text) if "<" in text[:2000] else text
