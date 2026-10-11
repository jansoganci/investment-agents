"""One polite request. A block (HTTP 429 / 403) raises `Blocked` and the caller stops at once (roadmap, Agent 1 rule 4).
The login cookie goes only to the host it was meant for: a redirect to another host is not followed."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = "investment-agents-eye (personal use; the site owner has allowed reading)"
BLOCK_STATUSES = (403, 429)


class Blocked(RuntimeError):
    """The site said "too many requests" / "access denied". Do not retry."""


class FetchError(RuntimeError):
    """The network failed (no answer, timeout)."""


@dataclass
class Response:
    url: str
    status: int
    headers: list          # [(name, value)]
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    def header(self, name: str) -> str | None:
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value
        return None

    def cookie_notes(self) -> list[str]:
        """Names and lifetimes of the cookies the site set — never their values."""
        notes = []
        for key, value in self.headers:
            if key.lower() != "set-cookie":
                continue
            parts = [p.strip() for p in value.split(";")]
            name = parts[0].split("=", 1)[0]
            life = [p for p in parts[1:] if p.lower().startswith(("max-age", "expires"))]
            notes.append(f"{name} ({', '.join(life) if life else 'session'})")
        return notes


def _host(url: str) -> str:
    host = urllib.parse.urlparse(url).hostname or ""
    return host.removeprefix("www.")


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _host(newurl) != _host(req.full_url):
            return None          # urllib then raises HTTPError(3xx); `fetch` hands it back as a Response
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_SameHostRedirect)


def fetch(url: str, cookie: str | None = None, timeout: float = 30) -> Response:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "tr,en;q=0.8"})
    if cookie:
        request.add_header("Cookie", cookie)
    try:
        with _opener.open(request, timeout=timeout) as answer:
            response = Response(url, answer.status, list(answer.headers.items()), answer.read())
    except urllib.error.HTTPError as error:
        response = Response(url, error.code, list(error.headers.items()), error.read())
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise FetchError(f"{url}: {error}") from None
    if response.status in BLOCK_STATUSES:
        raise Blocked(f"{url} answered {response.status}")
    return response
