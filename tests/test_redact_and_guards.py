"""Codex test of 2026-10-30: secrets in error messages, a loose sign-in link check, rows that could still be deleted."""

import sqlite3

import pytest

from agents.eye import magic_link
from agents.eye.sites import SITES
from shared import redact


def test_secrets_and_token_like_strings_are_hidden(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-live-1234567890abcdef")
    monkeypatch.setenv("SOME_COOKIE", "ghost-members-ssr=abcdefgh1234")
    text = "Incorrect API key provided: sk-live-1234567890abcdef (cookie ghost-members-ssr=abcdefgh1234) Bearer abc.def-ghi " + "a" * 40
    cleaned = redact.clean(text)
    for secret in ("sk-live", "abcdefgh1234", "abc.def", "a" * 40):
        assert secret not in cleaned
    assert redact.clean("HTTP 402: Insufficient balance for 2026-10-30") == "HTTP 402: Insufficient balance for 2026-10-30"
    assert redact.clean(None) == ""


def test_a_provider_error_message_never_carries_a_key(monkeypatch):
    from shared import search
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-secret-value-123456")
    text = search._error_text(401, b'{"error": {"message": "bad key sk-secret-value-123456"}}')
    assert "sk-secret" not in text and "HTTP 401" in text


@pytest.mark.parametrize("link", ["https://www.dragonomi.com/membership-unrelated/?token=x", "https://user@www.dragonomi.com/members/?token=x",
                                  "https://www.dragonomi.com:8443/members/?token=x", "https://www.dragonomi.com/members/"])
def test_a_loose_sign_in_link_is_refused(link):
    with pytest.raises(magic_link.LinkError):
        magic_link.target_of(SITES["dragonomi"], link)


def test_the_real_shape_of_a_sign_in_link_is_accepted():
    assert magic_link.target_of(SITES["dragonomi"], "https://www.dragonomi.com/members/?token=abc&action=signin")[1].startswith("/members/?token=")


def test_articles_tags_and_counts_cannot_lose_rows(db):
    db.execute("INSERT INTO articles (url, site, created_at) VALUES ('https://x/1/', 'emtia', 'x')")
    db.execute("INSERT INTO tags (tag, kind, source, created_at) VALUES ('t', 'other', 'ai', 'x')")
    db.execute("INSERT INTO counts (run_at, kind, key, label, posts_7d, posts_30d, has_card, created_at) VALUES ('x', 'stock', 'K', 'K', 1, 1, 0, 'x')")
    db.commit()
    for table in ("articles", "tags", "counts"):
        with pytest.raises(sqlite3.DatabaseError):
            db.execute(f"DELETE FROM {table}")
    db.execute("UPDATE tags SET kind = 'company' WHERE tag = 't'")          # a correction stays possible
    assert db.execute("SELECT kind FROM tags").fetchone()[0] == "company"
