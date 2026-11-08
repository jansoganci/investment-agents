from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from agents.pdf_reader import files, paths


def test_data_dir_from_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    monkeypatch.setenv("DATA_DIR", str(data))
    assert paths.data_dir() == data


def test_data_dir_from_settings_when_env_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    folder = tmp_path / "fromsettings"
    settings = tmp_path / "settings.yaml"
    settings.write_text(f"paths:\n  data_dir: {folder}\n", encoding="utf-8")
    monkeypatch.setattr(paths, "SETTINGS_FILE", settings)
    assert paths.data_dir() == folder


def test_data_dir_tilde_expanded(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_DIR", raising=False)
    settings = tmp_path / "settings.yaml"
    settings.write_text("paths:\n  data_dir: ~/pdfx\n", encoding="utf-8")
    monkeypatch.setattr(paths, "SETTINGS_FILE", settings)
    assert paths.data_dir() == Path.home() / "pdfx"


def test_data_dir_inside_drive_refused(tmp_path, monkeypatch):
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    monkeypatch.setenv("DATA_DIR", str(drive / "data"))
    with pytest.raises(paths.PathsError):
        paths.data_dir()


def test_drive_dir_missing(monkeypatch):
    monkeypatch.delenv("DRIVE_DIR", raising=False)
    with pytest.raises(paths.PathsError) as caught:
        paths.drive_dir()
    assert "DRIVE_DIR" in str(caught.value)


def test_folder_names(tmp_path, monkeypatch):
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    assert paths.new_dir() == drive / "PDF" / "New"
    assert paths.done_dir() == drive / "PDF" / "Done"
    assert paths.failed_dir() == drive / "PDF" / "Failed"
    assert paths.registry_file() == data / "pdf_registry.jsonl"
    assert paths.work_dir("ab") == data / "pdf_work" / "ab"


def test_ensure_dirs_creates_four_folders(tmp_path, monkeypatch):
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    paths.ensure_dirs()
    assert (drive / "PDF" / "New").is_dir()
    assert (drive / "PDF" / "Done").is_dir()
    assert (drive / "PDF" / "Failed").is_dir()
    assert (data / "pdf_work").is_dir()


def test_write_json_roundtrip_keeps_turkish(tmp_path):
    path = tmp_path / "note.json"
    files.write_json(path, {"name": "Şirket"})
    assert "Şirket" in path.read_text(encoding="utf-8")
    assert files.read_json(path) == {"name": "Şirket"}
    assert not path.with_name(path.name + ".tmp").exists()


def test_move_unique_adds_number(tmp_path):
    src = tmp_path / "in"
    dst = tmp_path / "out"
    src.mkdir()
    first = src / "x.pdf"
    first.write_bytes(b"1")
    assert files.move_unique(first, dst) == dst / "x.pdf"
    assert not first.exists()
    second = src / "x.pdf"
    second.write_bytes(b"2")
    assert files.move_unique(second, dst) == dst / "x (2).pdf"
    assert not second.exists()
    third = src / "x.pdf"
    third.write_bytes(b"3")
    assert files.move_unique(third, dst) == dst / "x (3).pdf"
    assert not third.exists()


def test_utc_stamp():
    now = datetime(2026, 11, 8, 20, 30, tzinfo=ZoneInfo("Europe/Istanbul"))
    assert files.utc_stamp(now) == "2026-11-08T17:30:00Z"
