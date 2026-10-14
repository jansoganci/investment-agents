import json
from datetime import timedelta

import pytest

from shared import alerts, clock, db as dbmod, summary, sunday
from shared.ai.fake import FakeAI

from .helpers import NOW, entry, stock

DAY = clock.today_local()


def texts(db, **kw):
    return [t for _, t in alerts.pending(db, **kw)]


def test_nothing_new_prints_nothing(db):
    assert alerts.run(db) is None


def test_a_holdings_grade_drop_is_an_alert_once(db):
    held = stock(db, "KO", grade="weak", in_portfolio="yes")
    entry(db, held, "mid", (NOW - timedelta(days=20)).date().isoformat())
    entry(db, held, "weak")
    first = alerts.run(db)
    assert first.startswith("ALERTS · 1 new") and f"GRADE DROP · KO: mid → weak ({DAY})" in first and "The decision is yours." in first
    assert alerts.run(db) is None


def test_a_drop_of_a_stock_i_do_not_hold_is_not_an_alert_and_a_rise_is_not_a_drop(db):
    other = stock(db, "PFE", grade="weak")
    entry(db, other, "mid", (NOW - timedelta(days=20)).date().isoformat())
    entry(db, other, "weak")
    held = stock(db, "KO", grade="solid", in_portfolio="yes")
    entry(db, held, "mid", (NOW - timedelta(days=20)).date().isoformat())
    entry(db, held, "solid")
    assert not any("GRADE DROP" in t for t in texts(db))


def test_a_stock_that_became_solid_is_a_green_list_alert_but_not_when_it_was_solid_already(db):
    new = stock(db, "NVDA", grade="solid")
    entry(db, new, "solid")                                              # first analysis, solid
    old = stock(db, "KO", grade="solid")
    entry(db, old, "solid", (NOW - timedelta(days=20)).date().isoformat())
    entry(db, old, "solid")                                              # solid again: nothing new
    archived = stock(db, "OLD", status="archived", grade="solid")
    entry(db, archived, "solid")
    out = texts(db)
    assert len(out) == 1 and out[0].startswith("GREEN LIST · NVDA is solid now")


def test_events_older_than_two_days_are_not_repeated_on_a_first_run(db):
    held = stock(db, "KO", grade="weak", in_portfolio="yes")
    entry(db, held, "mid", (NOW - timedelta(days=30)).date().isoformat())
    entry(db, held, "weak", (NOW - timedelta(days=10)).date().isoformat())
    assert alerts.run(db) is None


def test_a_pending_drop_alert_and_an_auditor_fail_are_alerts(db):
    sid = stock(db, "NKE", grade="mid")
    db.execute("INSERT INTO signals (kind, stock_id, date, detail, status, created_at) VALUES ('drop_alert', ?, ?, ?, 'pending', 'x')",
               (sid, DAY, json.dumps({"drawdown": -0.23})))
    db.execute("INSERT INTO signals (kind, stock_id, date, status, created_at) VALUES ('drop_alert', ?, ?, 'done', 'x')", (sid, DAY))
    db.execute("INSERT INTO audits (stock_id, audit, result, created_at) VALUES (?, 'figure', 'fail', ?)", (sid, clock.utc_iso()))
    db.execute("INSERT INTO audits (stock_id, audit, result, created_at) VALUES (?, 'figure', 'pass', ?)", (sid, clock.utc_iso()))
    db.execute("INSERT INTO audits (stock_id, audit, result, created_at) VALUES (NULL, 'event', 'fail', ?)", (clock.utc_iso(),))
    db.commit()
    out = texts(db)
    assert len(out) == 2
    assert any(t.startswith("DROP ALERT · NKE fell 20%") and "-0.23" in t for t in out)
    assert any(t.startswith("AUDITOR DISAGREES · NKE: the figure audit failed") for t in out)


def test_the_openrouter_spend_warning_comes_once_a_month(db):
    db.execute("INSERT INTO ai_calls (job, provider, model, cost_usd, outcome, created_at) VALUES ('strong', 'openrouter', 'm', 10.5, 'ok', ?)",
               (clock.utc_iso(),))
    db.execute("INSERT INTO ai_calls (job, provider, model, cost_usd, outcome, created_at) VALUES ('strong', 'anthropic', 'm', 50, 'ok', ?)",
               (clock.utc_iso(),))
    db.commit()
    first = alerts.run(db)
    assert "SPEND · OpenRouter has cost $10.50 this month (the warning is $10; the monthly limit is $15)" in first
    assert alerts.run(db) is None


def test_below_the_warning_there_is_no_spend_alert(db):
    db.execute("INSERT INTO ai_calls (job, provider, model, cost_usd, outcome, created_at) VALUES ('strong', 'openrouter', 'm', 9.9, 'ok', ?)",
               (clock.utc_iso(),))
    db.commit()
    assert alerts.run(db) is None


def test_the_command_prints_only_when_there_is_something(db, env, capsys):
    assert alerts.main([]) == 0 and capsys.readouterr().out == ""
    new = stock(db, "NVDA", grade="solid")
    entry(db, new, "solid")
    assert alerts.main([]) == 0 and "GREEN LIST · NVDA" in capsys.readouterr().out
    assert alerts.main(["x"]) == 2


# --- the Sunday chain -----------------------------------------------------------------------------------------------------------

@pytest.fixture
def chain(db, env, monkeypatch):
    from agents.analysis import run as analysis
    from agents.counter import count
    from agents.portfolio import run as portfolio
    from agents.research import run as research

    calls = []
    monkeypatch.setattr(count, "count", lambda conn, *a, **k: calls.append("counter"))
    monkeypatch.setattr(research, "weekly", lambda conn, sources, day, r: calls.append("research") or "RESEARCH\nNot researched — ZZZZ: SEC does not know it")
    monkeypatch.setattr(analysis, "weekly", lambda conn, sources, day, use_ai, run: calls.append("analysis") or "ANALYSIS · NVDA new 10-Q")
    monkeypatch.setattr(portfolio, "weekly", lambda conn, day: calls.append("portfolio") or "PORTFOLIO · $1,596")
    monkeypatch.setattr(analysis, "drop_alerts", lambda conn, sources, day, run=None: calls.append("drop_alerts") or "DROP ALERT · NVDA — thesis intact: fine")
    return calls


def test_the_chain_runs_in_the_decided_order_and_builds_one_summary(chain, db, env):
    lines = sunday.run_chain("2026-10-11")
    assert chain == ["counter", "research", "analysis", "portfolio", "drop_alerts"]
    text = "\n".join(lines)
    assert "PORTFOLIO · $1,596" in text and "ANALYSIS · NVDA new 10-Q" in text and "DROP ALERT · NVDA — thesis intact" in text
    assert "- Not researched — ZZZZ: SEC does not know it" in text                    # a stock Research could not do is reported
    assert (env["drive"] / "Weekly" / "2026-10-11-summary.md").exists()
    assert [r[0] for r in db.execute("SELECT job FROM runs ORDER BY id")] == ["counter", "research", "analysis", "portfolio", "drop_alerts"]
    assert {r[0] for r in db.execute("SELECT status FROM runs")} == {"ok"}


def test_a_failing_step_is_reported_and_the_next_ones_still_run(chain, db, env, monkeypatch):
    from agents.research import run as research

    def boom(*a, **k):
        chain.append("research")
        raise RuntimeError("web search is down")

    monkeypatch.setattr(research, "weekly", boom)
    lines = sunday.run_chain("2026-10-11")
    assert chain == ["counter", "research", "analysis", "portfolio", "drop_alerts"]
    text = "\n".join(lines)
    assert "THINGS THAT FAILED THIS WEEK" in text and "- research: RuntimeError: web search is down" in text and "PORTFOLIO · $1,596" in text
    assert db.execute("SELECT status FROM runs WHERE job = 'research'").fetchone() == ("error",)


def test_the_command_prints_the_summary(chain, db, env, capsys):
    assert sunday.main(["--day", "2026-10-11"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("SUNDAY SUMMARY · 2026-10-11") and "PORTFOLIO · $1,596" in out
    assert sunday.main(["--bogus"]) == 2
