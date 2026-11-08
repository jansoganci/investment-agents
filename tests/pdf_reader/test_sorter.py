from datetime import datetime, timezone

import pytest
from PIL import Image
from reportlab.lib.pagesizes import A4

from agents.pdf_reader import files
from agents.pdf_reader.sorter import run, sort_pdf
from tests.pdf_reader.helpers import body, make_pdf, text_lines

BERNSTEIN = (
    "See the Disclosure Appendix of this report for important disclosures "
    "and analyst certifications."
)
JPM = (
    "See page 13 for analyst certification and important disclosures, "
    "including non-US analyst disclosures."
)
NOW = datetime(2026, 11, 8, 17, 30, tzinfo=timezone.utc)


def _rows(first, count=8):
    rows = [[first, "Price", "Target"]]
    for number in range(count - 1):
        rows.append([str(number), "1", "2"])
    return rows


def _table(top, widths=None, rows=None):
    return {
        "op": "table", "x": 72, "top": top,
        "col_widths": widths or [120, 80, 80],
        "row_height": 18, "rows": rows or _rows("Name"),
    }


def _sort(tmp_path, pages, bookmarks=None):
    pdf = tmp_path / "report.pdf"
    make_pdf(pdf, pages, bookmarks=bookmarks)
    work = tmp_path / "work"
    work.mkdir()
    result = sort_pdf(pdf, work, "fp", "report.pdf", NOW)
    return result, work


def test_sorter_six_page_report(tmp_path):
    width, height = A4
    words = " ".join(f"w{i}" for i in range(30))
    pages = [
        [
            {"op": "text", "x": 72, "y": 800, "text": "Memory Weekly"},
            *text_lines(body(12)),
        ],
        [
            *text_lines(body(8)),
            {"op": "text", "x": 72, "y": 640, "text": BERNSTEIN},
            {"op": "text", "x": 72, "y": 600, "text": JPM},
            _table(300, rows=_rows("Old")),
        ],
        [
            _table(800, rows=_rows("New")),
            {"op": "rect", "x": 72, "y": 620, "w": 60, "h": 16, "color": ("gray", 0.749)},
            {"op": "text", "x": 75, "y": 624, "text": "#N/A", "size": 10, "color": ("gray", 0.753)},
            {"op": "text", "x": 72, "y": 580, "text": "APPENDIX – FINANCIAL FORECASTS"},
            *text_lines(body(6), top=540),
        ],
        [
            {"op": "image", "x": 0, "y": 0, "w": width, "h": height},
            *text_lines(body(20)),
        ],
        [
            {"op": "text", "x": 72, "y": 780, "text": "Disclosure Appendix"},
            *text_lines(body(10), top=740),
        ],
        [
            {"op": "text", "x": 72, "y": 780, "text": "SK hynix: Valuation Methodology"},
            {"op": "text", "x": 72, "y": 740, "text": words},
            {"op": "text", "x": 72, "y": 700, "text": "Risks"},
            {"op": "text", "x": 72, "y": 660, "text": "Please see www.example.com/risks for risks."},
        ],
    ]
    result, work = _sort(tmp_path, pages)
    got = result["pages"]
    assert result["disclosure_start"] == {
        "page": 5, "found_by": "heading", "text": "Disclosure Appendix",
    }
    assert [page["kind"] for page in got] == ["written"] * 3 + ["scanned"] + ["written"] * 2
    assert got[3]["kind_reason"] == "full_page_image"
    assert [page["part"] for page in got] == ["content"] * 4 + ["disclosure"] * 2
    assert [page["read"] for page in got] == [True, True, True, True, False, True]
    assert [page["read_sections"] for page in got] == [
        ["all"], ["all"], ["all"], ["all"], [], ["risks", "valuation"],
    ]
    for number in (1, 2, 3, 4, 6):
        assert (work / f"page-{number:03d}.png").is_file()
    assert not (work / "page-005.png").is_file()
    assert [page["prev_bottom_image"] for page in got] == [
        None, "page-001-bottom.png", "page-002-bottom.png", "page-003-bottom.png",
        None, "page-005-bottom.png",
    ]
    with Image.open(work / "page-001.png") as image:
        assert abs(image.size[0] - 1653) <= 1
        assert abs(image.size[1] - 2339) <= 1
    with Image.open(work / "page-001-bottom.png") as strip:
        assert abs(strip.size[1] - 702) <= 1
    assert got[2]["continuation"] == {
        "status": "continued", "header_from_page": 2, "signs": ["columns_match"],
    }
    assert got[3]["continuation"]["status"] == "not_checked"
    for index in (0, 4, 5):
        assert got[index]["continuation"] == {
            "status": "none", "header_from_page": None, "signs": [],
        }
    assert "#N/A" not in got[2]["text"]
    assert got[2]["dropped_invisible"] == 4
    assert result["notes"] == [{"code": "risks_only_link", "page": 6}]
    assert result["counts"] == {
        "content": 4,
        "content_written": 3,
        "content_scanned": 1,
        "disclosure": 2,
        "disclosure_read": 1,
        "images": 5,
        "dropped_invisible": 4,
    }
    assert got[3]["text"] is None


def test_bookmark_start(tmp_path):
    pages = [text_lines(body(8)) for _ in range(3)]
    result, _work = _sort(tmp_path, pages, [("Important Disclosures", 3)])
    assert result["disclosure_start"]["page"] == 3
    assert result["disclosure_start"]["found_by"] == "bookmark"


def test_no_disclosure_start(tmp_path):
    result, _work = _sort(tmp_path, [text_lines(body(8)), text_lines(body(8))])
    assert result["disclosure_start"] is None
    assert result["notes"] == [{"code": "disclosure_start_not_found", "page": None}]
    assert [page["part"] for page in result["pages"]] == ["content", "content"]


def test_header_chain(tmp_path):
    pages = [
        text_lines(body(8)),
        [*text_lines(body(8)), _table(300, rows=_rows("Start"))],
        [*text_lines(body(8), top=500), _table(800, rows=_rows("Next")), _table(300, rows=_rows("More"))],
        [*text_lines(body(8), top=500), _table(800, rows=_rows("Last"))],
    ]
    result, _work = _sort(tmp_path, pages)
    assert result["pages"][3]["continuation"]["header_from_page"] == 2


def test_run_reads_queue(tmp_path, monkeypatch):
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    new = drive / "PDF" / "New"
    new.mkdir(parents=True)
    pdf = new / "a.pdf"
    make_pdf(pdf, [text_lines(body(12))])
    work = data / "pdf_work" / "abc"
    work.mkdir(parents=True)
    files.write_json(work / "queue.json", {
        "version": 1,
        "fingerprint": "abc",
        "source_name": "a.pdf",
        "size_bytes": pdf.stat().st_size,
        "page_count": 1,
        "queued_at": "2026-11-08T17:30:00Z",
    })
    result = run(work, NOW)
    assert (work / "pages.json").is_file()
    assert not (work / "pages.json.tmp").exists()
    assert result["source_name"] == "a.pdf"
    assert result["fingerprint"] == "abc"


def test_run_missing_source(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DRIVE_DIR", str(tmp_path / "Investing"))
    work = tmp_path / "data" / "pdf_work" / "abc"
    work.mkdir(parents=True)
    files.write_json(work / "queue.json", {
        "version": 1,
        "fingerprint": "abc",
        "source_name": "missing.pdf",
        "size_bytes": 1,
        "page_count": 1,
        "queued_at": "2026-11-08T17:30:00Z",
    })
    with pytest.raises(FileNotFoundError):
        run(work, NOW)
