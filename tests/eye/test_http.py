import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from agents.eye import http


class Handler(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        Handler.seen.append({"path": self.path, "cookie": self.headers.get("Cookie"), "agent": self.headers.get("User-Agent")})
        if self.path == "/limit":
            self.send_response(429)
            self.end_headers()
        elif self.path == "/denied":
            self.send_response(403)
            self.end_headers()
        elif self.path == "/other-host":
            self.send_response(302)
            self.send_header("Location", f"http://localhost:{self.server.server_port}/landed")
            self.end_headers()
        elif self.path == "/same-host":
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/landed")
            self.end_headers()
        elif self.path == "/missing":
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Set-Cookie", "session=SECRET123; Max-Age=600; Path=/")
            self.send_header("Set-Cookie", "other=VALUE; Path=/")
            self.end_headers()
            self.wfile.write("Merhaba — çok güzel".encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    Handler.seen = []
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_fetch_sends_the_agent_and_the_cookie_and_reads_utf8(server):
    answer = http.fetch(server + "/ok", cookie="a=1; b=2")
    assert answer.status == 200 and answer.text == "Merhaba — çok güzel"
    assert Handler.seen[-1] == {"path": "/ok", "cookie": "a=1; b=2", "agent": http.USER_AGENT}


def test_no_cookie_header_when_none_is_given(server):
    http.fetch(server + "/ok")
    assert Handler.seen[-1]["cookie"] is None


def test_cookie_notes_show_names_and_lifetimes_but_never_values(server):
    notes = http.fetch(server + "/ok").cookie_notes()
    assert notes == ["session (Max-Age=600)", "other (session)"]
    assert "SECRET123" not in " ".join(notes)


@pytest.mark.parametrize("path", ["/limit", "/denied"])
def test_429_and_403_are_a_block(server, path):
    with pytest.raises(http.Blocked):
        http.fetch(server + path)


def test_other_statuses_come_back_to_the_caller(server):
    assert http.fetch(server + "/missing").status == 404


def test_a_redirect_to_another_host_is_not_followed_so_the_cookie_stays_home(server):
    answer = http.fetch(server + "/other-host", cookie="secret=1")
    assert answer.status == 302
    assert [s["path"] for s in Handler.seen] == ["/other-host"]       # /landed was never asked


def test_a_redirect_inside_the_same_host_is_followed(server):
    answer = http.fetch(server + "/same-host", cookie="secret=1")
    assert answer.status == 200 and Handler.seen[-1]["path"] == "/landed"


def test_a_dead_address_is_a_fetch_error():
    with pytest.raises(http.FetchError):
        http.fetch("http://127.0.0.1:9/", timeout=2)


def test_a_cookie_with_a_line_break_is_refused_and_never_shown(monkeypatch):
    secret = "ghost-members-ssr=TOPSECRET\nnext=2"
    with pytest.raises(http.FetchError) as info:
        http.fetch("http://127.0.0.1:9/x", cookie=secret)
    assert "TOPSECRET" not in str(info.value) and "set_cookie" in str(info.value)


def test_an_odd_error_of_the_http_library_never_carries_the_cookie_text(monkeypatch):
    def boom(*a, **k):
        raise ValueError("Invalid header value b'ghost-members-ssr=TOPSECRET'")
    monkeypatch.setattr(http._opener, "open", boom)
    with pytest.raises(http.FetchError) as info:
        http.fetch("http://127.0.0.1:9/x", cookie="ghost-members-ssr=TOPSECRET")
    assert "TOPSECRET" not in str(info.value) and "ValueError" in str(info.value)


def test_a_body_cut_by_the_server_is_a_fetch_error(monkeypatch):
    import http.client as stdlib_client

    def boom(*a, **k):
        raise stdlib_client.IncompleteRead(b"x")
    monkeypatch.setattr(http._opener, "open", boom)
    with pytest.raises(http.FetchError):
        http.fetch("http://127.0.0.1:9/x")


def test_a_redirect_from_https_to_plain_http_is_not_followed():
    handler = http._SameHostRedirect()
    req = http.urllib.request.Request("https://www.example.com/a")
    assert handler.redirect_request(req, None, 302, "Found", {}, "http://www.example.com/b") is None
    assert handler.redirect_request(req, None, 302, "Found", {}, "https://www.example.com/b") is not None
