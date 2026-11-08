from datetime import datetime, timedelta, timezone

import pytest

from agents.pdf_reader import files, gate, paths, registry
from tests.pdf_reader.helpers import body, garbage_pdf, make_pdf, text_lines


def _later() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=10)


def _look(now: datetime | None = None, sleep=lambda _seconds: None):
    return gate.look(_later() if now is None else now, sleep)


@pytest.fixture
def gate_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    new = drive / "PDF" / "New"
    return {
        "data": data,
        "new": new,
        "done": drive / "PDF" / "Done",
        "failed": drive / "PDF" / "Failed",
    }


def _good(folder, name="a.pdf"):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    make_pdf(path, [text_lines(body(12))] * 2)
    return path


def _listed(report: gate.LookReport) -> set[str]:
    names = set(report.waiting_sync) | set(report.not_pdf) | set(report.missing)
    groups = (
        report.queued, report.in_progress, report.source_changed,
        report.duplicates_waiting, report.moved, report.failed,
    )
    for group in groups:
        for row in group:
            names.add(row[0])
    return names


def test_empty_new_folder(gate_env):
    report = _look()
    assert report.queued == []
    assert report.in_progress == []
    assert report.source_changed == []
    assert report.duplicates_waiting == []
    assert report.moved == []
    assert report.failed == []
    assert report.waiting_sync == []
    assert report.not_pdf == []
    assert report.missing == []
    assert gate_env["new"].is_dir()
    assert gate_env["done"].is_dir()
    assert gate_env["failed"].is_dir()


def test_good_pdf_is_queued(gate_env):
    pdf = _good(gate_env["new"])
    report = _look()
    fp = gate.fingerprint(pdf)
    assert report.queued == [("a.pdf", fp, 2)]
    data = files.read_json(paths.work_dir(fp) / "queue.json")
    assert list(data) == ["version", "fingerprint", "source_name", "size_bytes", "page_count", "queued_at"]
    assert data["source_name"] == "a.pdf"
    assert data["page_count"] == 2
    rows = registry.load()
    assert len(rows) == 1 and rows[0]["event"] == "queued"
    assert pdf.is_file()


def test_second_look_does_not_queue_again(gate_env):
    pdf = _good(gate_env["new"])
    _look()
    fp = gate.fingerprint(pdf)
    report = _look()
    assert report.in_progress == [("a.pdf", fp)]
    assert [row["event"] for row in registry.load()].count("queued") == 1


def test_fresh_file_waits_for_sync(gate_env):
    _good(gate_env["new"])
    report = _look(datetime.now(timezone.utc))
    assert report.waiting_sync == ["a.pdf"]
    assert report.queued == []
    assert not paths.registry_file().exists()


def test_file_changing_waits(gate_env):
    pdf = _good(gate_env["new"])

    def sleep(_seconds):
        with pdf.open("ab") as handle:
            handle.write(b"x")

    report = _look(sleep=sleep)
    assert report.waiting_sync == ["a.pdf"]


def test_empty_file_waits(gate_env):
    gate_env["new"].mkdir(parents=True)
    (gate_env["new"] / "a.pdf").write_bytes(b"")
    report = _look()
    assert report.waiting_sync == ["a.pdf"]


def test_temp_and_hidden_names_ignored(gate_env):
    new = gate_env["new"]
    new.mkdir(parents=True)
    for name in (".~tmp.pdf", "~$a.pdf", ".hidden.pdf"):
        (new / name).write_bytes(b"x")
    (new / "folder.pdf").mkdir()
    (new / "notes.txt").write_text("hi", encoding="utf-8")
    _good(new, "A.PDF")
    report = _look()
    assert report.not_pdf == ["notes.txt"]
    assert report.queued[0][0] == "A.PDF"
    hidden = {".~tmp.pdf", "~$a.pdf", ".hidden.pdf", "folder.pdf"}
    assert hidden.isdisjoint(_listed(report))


def test_renamed_copy_same_look(gate_env):
    a = _good(gate_env["new"])
    b = gate_env["new"] / "b.pdf"
    b.write_bytes(a.read_bytes())
    report = _look()
    fp = gate.fingerprint(a)
    assert report.queued == [("a.pdf", fp, 2)]
    assert report.duplicates_waiting == [("b.pdf", "a.pdf")]
    assert a.is_file() and b.is_file()
    events = [row["event"] for row in registry.load()]
    assert events.count("queued") == 1
    assert events.count("duplicate") == 1


def test_copy_later_noted_once(gate_env):
    a = _good(gate_env["new"])
    _look()
    b = gate_env["new"] / "b.pdf"
    b.write_bytes(a.read_bytes())
    _look()
    _look()
    dupes = [row for row in registry.load() if row["event"] == "duplicate"]
    assert len(dupes) == 1


def test_broken_goes_to_failed(gate_env):
    new = gate_env["new"]
    new.mkdir(parents=True)
    bad = garbage_pdf(new / "bad.pdf")
    fp = gate.fingerprint(bad)
    report = _look()
    detail = report.failed[0][2]
    assert report.failed == [("bad.pdf", "broken", detail)]
    assert (gate_env["failed"] / "bad.pdf").is_file()
    assert not bad.exists()
    assert not paths.work_dir(fp).exists()


def test_encrypted_goes_to_failed(gate_env):
    new = gate_env["new"]
    new.mkdir(parents=True)
    make_pdf(new / "locked.pdf", [text_lines(body(4))], encrypt="secret")
    report = _look()
    assert report.failed[0][1] == "encrypted"


def test_same_broken_bytes_again_moved_to_failed(gate_env):
    new = gate_env["new"]
    new.mkdir(parents=True)
    garbage_pdf(new / "bad.pdf")
    _look()
    same = new / "bad2.pdf"
    same.write_bytes((gate_env["failed"] / "bad.pdf").read_bytes())
    report = _look()
    assert report.moved == [("bad2.pdf", "Failed")]
    moved = [row for row in registry.load() if row["event"] == "duplicate_moved"]
    assert len(moved) == 1


def test_failed_name_collision(gate_env):
    new = gate_env["new"]
    new.mkdir(parents=True)
    failed = gate_env["failed"]
    failed.mkdir(parents=True)
    (failed / "bad.pdf").write_bytes(b"already here")
    garbage_pdf(new / "bad.pdf")
    _look()
    assert (failed / "bad (2).pdf").is_file()
    assert (failed / "bad.pdf").read_bytes() == b"already here"


def test_copy_of_mailed_file_goes_to_done(gate_env):
    a = _good(gate_env["new"])
    _look()
    fp = gate.fingerprint(a)
    a.rename(gate_env["done"] / "a.pdf")
    registry.append("mailed", fp, _later(), name="a.pdf")
    b = gate_env["new"] / "b.pdf"
    b.write_bytes((gate_env["done"] / "a.pdf").read_bytes())
    report = _look()
    assert report.moved == [("b.pdf", "Done")]
    assert (gate_env["done"] / "b.pdf").is_file()
    moved = [row for row in registry.load() if row["event"] == "duplicate_moved"]
    assert len(moved) == 1 and moved[0]["to"] == "Done"


def test_mailed_file_never_queued_again(gate_env):
    a = _good(gate_env["new"])
    _look()
    fp = gate.fingerprint(a)
    a.rename(gate_env["done"] / "a.pdf")
    registry.append("mailed", fp, _later(), name="a.pdf")
    c = gate_env["new"] / "c.pdf"
    c.write_bytes((gate_env["done"] / "a.pdf").read_bytes())
    _look()
    assert (gate_env["done"] / "c.pdf").is_file()
    assert [row["event"] for row in registry.load()].count("queued") == 1


def test_three_failures_move_to_failed(gate_env):
    pdf = _good(gate_env["new"])
    _look()
    fp = gate.fingerprint(pdf)
    now = _later()
    assert gate.record_attempt_failure(fp, "sorter", "boom", now) == (1, False)
    assert pdf.is_file()
    assert gate.record_attempt_failure(fp, "sorter", "boom", now) == (2, False)
    assert pdf.is_file()
    assert gate.record_attempt_failure(fp, "sorter", "boom", now) == (3, True)
    assert (gate_env["failed"] / "a.pdf").is_file()
    assert not pdf.exists()
    assert registry.status(registry.load(), fp) == "failed"


def test_waiting_copy_follows_failed_original(gate_env):
    a = _good(gate_env["new"])
    _look()
    fp = gate.fingerprint(a)
    b = gate_env["new"] / "b.pdf"
    b.write_bytes(a.read_bytes())
    now = _later()
    for _ in range(3):
        gate.record_attempt_failure(fp, "sorter", "boom", now)
    report = _look()
    assert report.moved == [("b.pdf", "Failed")]
    assert (gate_env["failed"] / "b.pdf").is_file()


def test_renamed_source_is_followed(gate_env):
    pdf = _good(gate_env["new"])
    _look()
    fp = gate.fingerprint(pdf)
    pdf.rename(gate_env["new"] / "z.pdf")
    report = _look()
    assert report.source_changed == [("a.pdf", "z.pdf")]
    data = files.read_json(paths.work_dir(fp) / "queue.json")
    assert data["source_name"] == "z.pdf"
    assert report.in_progress == [("z.pdf", fp)]


def test_missing_source_reported(gate_env):
    pdf = _good(gate_env["new"])
    _look()
    fp = gate.fingerprint(pdf)
    before = registry.load()
    pdf.unlink()
    report = _look()
    assert report.missing == ["a.pdf"]
    assert registry.load() == before
    assert registry.status(registry.load(), fp) == "in_progress"
