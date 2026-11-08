from datetime import datetime, timezone

import pytest

from agents.pdf_reader import paths, registry

NOW = datetime(2026, 11, 8, 17, 30, tzinfo=timezone.utc)
FP = "3f1c"
OTHER = "aaaa"


@pytest.fixture(autouse=True)
def registry_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))


def test_load_missing_is_empty():
    assert registry.load() == []


def test_append_adds_one_line_and_keeps_old():
    registry.append("queued", FP, NOW, name="a.pdf", size_bytes=10, page_count=2)
    path = paths.registry_file()
    first = path.read_bytes().splitlines()[0]
    registry.append("sorted", FP, NOW, name="a.pdf", page_count=2)
    lines = path.read_bytes().splitlines()
    assert lines[0] == first
    assert len(lines) == 2


def test_unknown_event_refused():
    with pytest.raises(ValueError):
        registry.append("nope", FP, NOW)
    assert not paths.registry_file().exists()


def test_bad_line_raises():
    path = paths.registry_file()
    path.parent.mkdir(parents=True)
    path.write_text('{"at": "2026-11-08T17:30:00Z", "event": "queued", "fingerprint": "3f1c"}\nnot-json\n', encoding="utf-8")
    with pytest.raises(registry.RegistryError) as caught:
        registry.load()
    assert "line 2" in str(caught.value)


def test_status_order():
    assert registry.status([], FP) == "new"
    queued = [{"event": "queued", "fingerprint": FP}]
    assert registry.status(queued, FP) == "in_progress"
    assert registry.status([{"event": "failed", "fingerprint": FP}], FP) == "failed"
    assert registry.status([{"event": "mailed", "fingerprint": FP}], FP) == "mailed"
    both = queued + [{"event": "failed", "fingerprint": FP}, {"event": "mailed", "fingerprint": FP}]
    assert registry.status(both, FP) == "mailed"


def test_attempts_counts_only_this_file():
    rows = [
        {"event": "attempt_failed", "fingerprint": FP},
        {"event": "attempt_failed", "fingerprint": FP},
        {"event": "attempt_failed", "fingerprint": OTHER},
        {"event": "queued", "fingerprint": FP},
    ]
    assert registry.attempts(rows, FP) == 2
    assert registry.attempts(rows, OTHER) == 1


def test_source_name_follows_source_changed():
    rows = [
        {"event": "queued", "fingerprint": FP, "name": "a.pdf"},
        {"event": "source_changed", "fingerprint": FP, "name": "z.pdf"},
        {"event": "queued", "fingerprint": OTHER, "name": "b.pdf"},
    ]
    assert registry.source_name(rows, FP) == "z.pdf"
    assert registry.source_name([], FP) is None


def test_has_duplicate_note():
    rows = [{"event": "duplicate", "fingerprint": FP, "name": "b.pdf"}]
    assert registry.has_duplicate_note(rows, FP, "b.pdf") is True
    assert registry.has_duplicate_note(rows, FP, "c.pdf") is False
    assert registry.has_duplicate_note(rows, OTHER, "b.pdf") is False
