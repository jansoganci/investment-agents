import json
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from agents.research import news, page
from shared.ai.fake import FakeAI

TODAY = date(2026, 10, 12)
URL = "https://news.example/acme-cfo"
PAGE = ("Acme Corp announced today that its chief financial officer, Jane Roe, has resigned effective immediately. "
        "The company also withdrew its full-year outlook.")
QUOTE = "its chief financial officer, Jane Roe, has resigned effective immediately"


def event(**kw):
    base = {"summary": "The CFO resigned and the outlook was withdrawn.", "date": "2026-09-15", "source_url": URL, "quote": QUOTE,
            "scope": "company_specific", "class": "serious_negative", "serious_type": "sudden_ceo_or_cfo_departure"}
    base.update(kw)
    return base


def model(events=None, links=None, story="It sells engines. It earns from engines and parts.", auditor_verdict="pass"):
    def handler(job, system, prompt):
        if job == "auditor":
            return [{"id": "e1", "verdict": auditor_verdict, "quote": QUOTE, "reason": "it says so"}]
        return {"story": story, "events": events if events is not None else [], "commodity_links": links or []}
    return handler


def install(monkeypatch, handler, urls=(URL,)):
    fake = FakeAI(handler)
    fake.sources = [{"url": u, "title": "t", "cited_text": None} for u in urls]
    return fake.install(monkeypatch)


def fetcher(text=PAGE, error=None):
    def fetch(url, max_bytes=0):
        if error:
            raise page.PageError(error)
        return text
    return fetch


def search(db, **kw):
    return news.search(db, None, "ACME", "Acme Corp", today=TODAY, fetch=kw.get("fetch", fetcher()))


def test_a_confirmed_serious_negative_scores_zero_and_is_audited(db, monkeypatch):
    fake = install(monkeypatch, model([event()]))
    n = search(db)
    assert n.points == 0 and n.events[0].status == "confirmed" and "serious negative confirmed" in n.reason
    assert [c[0] for c in fake.calls] == ["strong", "auditor"]
    assert db.execute("SELECT audit, result FROM audits").fetchone() == ("event", "pass")
    assert n.events[0].audit_id == db.execute("SELECT id FROM audits").fetchone()[0]
    assert n.story.startswith("It sells engines.")


@pytest.mark.parametrize("change, why", [
    (dict(source_url="https://elsewhere.example/x"), "not among the pages the search returned"),
    (dict(source_url=None), "no source address"),
    (dict(date="2024-01-01"), "outside the last 365 days"),
    (dict(date="soon"), "no usable date"),
    (dict(quote="a sentence that is not on the page at all, invented"), "the quote is not on the source page"),
])
def test_a_serious_negative_that_fails_a_code_check_is_not_counted(db, monkeypatch, change, why):
    fake = install(monkeypatch, model([event(**change)]))
    n = search(db)
    assert n.points == 1 and n.events[0].status == "not_confirmed" and why in n.events[0].note
    assert "were not confirmed and are not counted" in n.reason
    assert [c[0] for c in fake.calls] == ["strong"]                      # the auditor is not asked for what code already refused


def test_the_auditor_can_refuse_what_the_code_accepted(db, monkeypatch):
    install(monkeypatch, model([event()], auditor_verdict="fail"))
    n = search(db)
    assert n.points == 1 and n.events[0].status == "not_confirmed" and "auditor said fail" in n.events[0].note


def test_a_source_page_that_cannot_be_read_does_not_confirm(db, monkeypatch):
    install(monkeypatch, model([event()]))
    n = search(db, fetch=fetcher(error="HTTP 403"))
    assert n.events[0].status == "not_confirmed" and "could not be read (HTTP 403)" in n.events[0].note


def test_a_general_risk_is_not_a_serious_negative(db, monkeypatch):
    install(monkeypatch, model([event(scope="general_risk")]))
    n = search(db)
    assert n.points == 1 and n.events[0].status == "not_checked" and "general risk" in n.events[0].note


def test_a_class_serious_negative_without_a_listed_type_becomes_other(db, monkeypatch):
    install(monkeypatch, model([event(serious_type="stock_dipped")]))
    n = search(db)
    assert n.events[0].klass == "other" and n.points == 1


def test_an_important_positive_with_a_source_scores_two(db, monkeypatch):
    install(monkeypatch, model([event(**{"class": "important_positive", "serious_type": None, "summary": "A large new contract."})]))
    n = search(db)
    assert n.points == 2 and "important positive: A large new contract." in n.reason and n.events[0].status == "not_checked"


def test_an_important_positive_older_than_90_days_is_not_counted(db, monkeypatch):
    install(monkeypatch, model([event(**{"class": "important_positive", "serious_type": None, "date": "2026-02-18"})]))
    n = search(db)
    assert n.points == 1 and n.events[0].status == "not_confirmed" and "outside the last 90 days" in n.events[0].note


def test_an_important_positive_without_a_usable_date_is_not_counted(db, monkeypatch):
    install(monkeypatch, model([event(**{"class": "important_positive", "serious_type": None, "date": None})]))
    assert search(db).points == 1


def test_an_important_positive_without_a_search_source_is_not_counted(db, monkeypatch):
    install(monkeypatch, model([event(**{"class": "important_positive", "serious_type": None, "source_url": "https://made.up/x"})]))
    assert search(db).points == 1


def test_a_serious_negative_beats_an_important_positive(db, monkeypatch):
    positive = event(**{"class": "important_positive", "serious_type": None, "summary": "Contract."})
    install(monkeypatch, model([positive, event()]))
    assert search(db).points == 0


def test_no_events_is_one_point(db, monkeypatch):
    install(monkeypatch, model([]))
    n = search(db)
    assert n.points == 1 and "no confirmed serious negative and no important positive found" in n.reason


def test_when_the_news_cannot_be_checked_it_is_unclear_not_bad(db, monkeypatch):
    down = FakeAI(model())
    down.fail = {"anthropic"}
    down.install(monkeypatch)
    n = search(db)
    assert n.points == 1 and n.error and n.reason.startswith("unclear") and n.events == []


def test_an_unusable_answer_is_unclear(db, monkeypatch):
    install(monkeypatch, lambda *a: "sorry, no json")
    n = search(db)
    assert n.points == 1 and "could not be used" in n.error


def test_the_search_is_asked_with_the_web_tool_the_ticker_and_the_commodity_names(db, monkeypatch):
    fake = install(monkeypatch, model([]))
    search(db)
    job, system, prompt = fake.calls[0]
    assert "Ticker: ACME" in prompt and "Today: 2026-10-12" in prompt
    assert "crude oil" in system and "sudden_ceo_or_cfo_departure" in system and "ignore" in system


def test_commodity_links_must_use_a_listed_name_a_role_and_a_search_source(db, monkeypatch):
    links = [{"commodity": "Copper", "role": "producer", "source_url": URL},
             {"commodity": "unobtainium", "role": "producer", "source_url": URL},
             {"commodity": "gold", "role": "buyer", "source_url": URL},
             {"commodity": "wheat", "role": "user", "source_url": "https://made.up/x"},
             {"commodity": "copper", "role": "producer", "source_url": URL}]
    install(monkeypatch, model([], links))
    assert search(db).links == [{"commodity": "copper", "role": "producer", "source": URL}]


def test_events_are_saved_with_their_status_and_note(db, monkeypatch):
    install(monkeypatch, model([event(date="2024-01-01")]))
    n = search(db)
    news.save_events(db, "ACME", "2026-W41", n.events)
    assert db.execute("SELECT ticker, week, class, status, note FROM news_events").fetchone() == (
        "ACME", "2026-W41", "serious_negative", "not_confirmed", "the date 2024-01-01 is outside the last 365 days")


# --- the page fetcher ----------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "http://localhost:8000/", "http://10.0.0.5/", "http://192.168.1.1/",
                                 "http://169.254.169.254/latest", "file:///etc/passwd", "ftp://example.com/x", "not a url"])
def test_a_private_or_odd_address_is_never_fetched(url):
    assert not page.public_address(url)
    with pytest.raises(page.PageError, match="not a public web address"):
        page.fetch_text(url)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/pdf":
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.end_headers()
            self.wfile.write(b"%PDF")
        elif self.path == "/gone":
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<html><body><script>x()</script><p>Merhaba dünya</p><p>İkinci satır</p></body></html>".encode())

    def log_message(self, *a):
        pass


@pytest.fixture
def local(monkeypatch):
    monkeypatch.setattr(page, "public_address", lambda url: True)          # the test server is on this machine
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_a_page_becomes_plain_text(local):
    assert page.fetch_text(local + "/x").splitlines() == ["Merhaba dünya", "İkinci satır"]


def test_a_non_text_page_and_an_http_error_are_page_errors(local):
    with pytest.raises(page.PageError, match="not a text page"):
        page.fetch_text(local + "/pdf")
    with pytest.raises(page.PageError, match="HTTP 404"):
        page.fetch_text(local + "/gone")
