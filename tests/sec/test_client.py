"""The SEC client: an answer that is not JSON is a SecError like any other SEC failure (security audit 2026-11-07, T3 b/c)."""

import pytest

import shared.sec as sec


@pytest.mark.parametrize("body", [b"<html><body>Request Rate Threshold Exceeded</body></html>", b'{"cik": 21344, "facts": {',
                                  b"\xff\xfe\x00"])
def test_a_body_that_is_not_json_is_a_sec_error(monkeypatch, body):
    monkeypatch.setattr(sec, "_get_bytes", lambda url, tries=3: body)
    with pytest.raises(sec.SecError, match="not JSON"):
        sec.company_facts(21344)


def test_valid_json_still_reads(monkeypatch):
    monkeypatch.setattr(sec, "_get_bytes", lambda url, tries=3: b'{"cik": 21344, "facts": {}}')
    assert sec.company_facts(21344) == {"cik": 21344, "facts": {}}
