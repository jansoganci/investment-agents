"""shared/bulletin/run: the whole job against stand-ins — saved once a day, reused, forced, dry, the window that carries on, a failed
writer."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from shared import clock, drive
from shared.ai.fake import FakeAI
from shared.bulletin import __main__ as cli
from shared.bulletin import run as bulletin_run
from shared.search import Hit
from tests.bulletin.test_gather import add_post, add_stock, add_tag, card_text

NOW = datetime(2026, 10, 29, 5, 0, tzinfo=timezone.utc)          # Thursday 08:00 Turkey time


class Run:
    id, cost_usd = None, 0.0

    def add_cost(self, usd):
        self.cost_usd += usd


def answers(job, system, prompt):
    if job == "strong":
        return {"macro": [{"text": "Brent rose above 115 a barrel.", "sources": ["W1"], "rank": 1}],
                "stocks": {"KO": [{"text": "KO raised prices 4%.", "sources": ["P7"], "thesis_point": 2}]}}
    return {k: "TR: " + v for k, v in json.loads(prompt).items()}      # the cheap model: every item, numbers untouched


@pytest.fixture
def world(db, env, monkeypatch):
    add_stock(db, "KO", "Coca-Cola", held="yes", cik="21344", card=card_text())
    add_tag(db, "Coca-Cola", "KO")
    add_post(db, 7, "2026-10-28T10:00:00Z", "Cola news", tags=["Coca-Cola"], text="KO raised prices 4%.")
    fake = FakeAI(answers).install(monkeypatch)
    kwargs = dict(search_fn=lambda q, **kw: [Hit("Brent", "https://x/1", "Reuters", "2026-10-28T20:00:00+00:00", "s",
                                                 "Brent rose above 115 a barrel.", 2.0, 3)],
                  submissions=lambda cik: {}, earnings_fn=lambda t: ["2026-10-30"])
    return {"db": db, "fake": fake, "kwargs": kwargs, "run": Run()}


def build(w, now=NOW, **options):
    return bulletin_run.build(w["db"], w["run"], now=now, gather_kwargs=w["kwargs"], **options)


def rows(db):
    return db.execute("SELECT day, window_start, window_end, void FROM bulletins ORDER BY id").fetchall()


def test_a_bulletin_is_built_saved_in_the_database_and_in_drive(world):
    text = build(world)
    assert text.startswith("☀️ SABAH BÜLTENİ · 29 Ekim 2026, Perşembe")
    assert "TR: Brent rose above 115 a barrel. [W1]" in text and "KO · TR: KO raised prices 4%. [ED2]" in text
    assert '↳ Tez bozucu 2 ile ilgili: "debt grows"' in text and "📌 KO bilançosu: 30 Ekim" in text
    assert [c[0] for c in world["fake"].calls] == ["strong", "cheap"]
    row = world["db"].execute("SELECT turkish, english, sources, cost_usd FROM bulletins").fetchone()
    assert row[0] == text and row[3] == pytest.approx(world["run"].cost_usd) and row[3] > 0
    assert json.loads(row[1])[0]["text"] == "Brent rose above 115 a barrel." and json.loads(row[2])[0]["tag"] == "W"
    saved = (drive.bulletin() / "2026-10-29.md").read_text(encoding="utf-8")
    assert saved.startswith("---\nbulletin: 2026-10-29\npublish: no\n---\n\n☀️ SABAH BÜLTENİ") and saved.rstrip().endswith(text.rstrip())
    assert rows(world["db"]) == [("2026-10-29", "2026-10-28T05:15:00Z", "2026-10-29T05:00:00Z", 0)]


def test_a_second_run_the_same_day_prints_the_saved_text_and_spends_nothing(world):
    first = build(world)
    calls, cost = len(world["fake"].calls), world["run"].cost_usd
    assert build(world) == first
    assert len(world["fake"].calls) == calls and world["run"].cost_usd == cost and len(rows(world["db"])) == 1


def test_force_builds_again_and_voids_the_old_row(world):
    build(world)
    build(world, force=True)
    assert [r[3] for r in rows(world["db"])] == [1, 0] and len(world["fake"].calls) == 4


def test_dry_saves_nothing(world):
    assert build(world, dry=True).startswith("☀️ SABAH BÜLTENİ")
    assert rows(world["db"]) == [] and not (drive.bulletin() / "2026-10-29.md").exists()


def test_the_next_window_starts_where_the_last_one_ended(world):
    build(world)
    build(world, now=NOW + timedelta(days=1))
    assert [(r[0], r[1]) for r in rows(world["db"])] == [("2026-10-29", "2026-10-28T05:15:00Z"), ("2026-10-30", "2026-10-29T05:00:00Z")]


def test_a_long_gap_is_capped_at_four_days(world):
    build(world)
    build(world, now=NOW + timedelta(days=10))
    assert rows(world["db"])[1][1] == clock.utc_iso(NOW + timedelta(days=10) - timedelta(days=4))


def test_a_failed_writer_still_sends_the_figures_but_saves_nothing(world, monkeypatch):
    FakeAI(lambda job, system, prompt: "not json").install(monkeypatch)
    text = build(world)
    assert "📊 RAKAMLAR" in text and "⚠ Haberler yazılamadı (ValueError:" in text and "📌 KO bilançosu: 30 Ekim" in text
    assert rows(world["db"]) == []                                  # the next run covers this window again
    assert "ℹ️ 1 kaynak ya da adım alınamadı" in text


def test_the_commands_show_and_dry_work_on_an_empty_database(db, capsys, monkeypatch):
    FakeAI(answers).install(monkeypatch)
    assert cli.main(["--show"]) == 0
    assert capsys.readouterr().out.strip() == "No bulletin has been saved yet."
    assert cli.main(["--dry"]) == 0                                 # no key, no stocks: only the figures, a note and the empty-day line
    out = capsys.readouterr().out
    assert out.startswith("☀️ SABAH BÜLTENİ") and "Kaynaklardan yeni bir haber gelmedi." in out and "ℹ️ 1 kaynak ya da adım alınamadı" in out
    assert cli.main(["--nonsense"]) == 2
