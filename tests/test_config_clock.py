from datetime import datetime, timezone

import pytest

from shared import clock, config


# --- SQLite never goes in Drive (AGENTS.md, "Technical") ---

def test_data_dir_inside_drive_dir_is_refused(env, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(env["drive"] / "data"))
    with pytest.raises(config.UnsafePath):
        config.data_dir()


def test_data_dir_in_a_cloud_folder_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("DRIVE_DIR", raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "Library" / "CloudStorage" / "GoogleDrive-me" / "My Drive" / "data"))
    with pytest.raises(config.UnsafePath):
        config.db_path()


def test_normal_data_dir_is_fine(env):
    assert config.db_path() == env["data"] / "investment-agents.sqlite"


# --- Times: stored in UTC, shown in Turkey time (roadmap section 5) ---

def test_time_zone_comes_from_settings():
    assert clock.LOCAL.key == config.settings()["timezone"] == "Europe/Istanbul"


def test_utc_iso_format_and_round_trip():
    dt = datetime(2026, 10, 4, 20, 15, 3, tzinfo=timezone.utc)
    assert clock.utc_iso(dt) == "2026-10-04T20:15:03Z"
    assert clock.parse_utc("2026-10-04T20:15:03Z") == dt


def test_local_time_is_stored_as_utc():
    assert clock.utc_iso(datetime(2026, 10, 4, 23, 15, 3, tzinfo=clock.LOCAL)) == "2026-10-04T20:15:03Z"


def test_shown_in_turkey_time():
    assert clock.show("2026-10-04T22:30:00Z") == "2026-10-05 01:30"
    assert clock.show(None) == "—"


def test_today_is_the_turkish_date():
    assert clock.today_local(datetime(2026, 10, 4, 22, 30, tzinfo=timezone.utc)) == "2026-10-05"
