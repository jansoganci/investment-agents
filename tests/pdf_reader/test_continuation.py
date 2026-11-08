import pdfplumber

from agents.pdf_reader.continuation import has_continued_line, judge
from tests.pdf_reader.helpers import body, make_pdf, text_lines


def _rows(first, count):
    rows = [[first, "Price", "Target"]]
    for number in range(count - 1):
        rows.append([str(number), "1", "2"])
    return rows


def _table(top, widths, rows):
    return {
        "op": "table", "x": 72, "top": top, "col_widths": widths,
        "row_height": 18, "rows": rows,
    }


def _open(tmp_path, name, pages):
    pdf = tmp_path / name
    make_pdf(pdf, pages)
    return pdfplumber.open(pdf)


def test_same_columns_runs_over(tmp_path):
    widths = [120, 80, 80]
    doc = _open(tmp_path, "same.pdf", [
        [_table(300, widths, _rows("Old", 8))],
        [_table(800, widths, _rows("New", 8))],
    ])
    try:
        assert judge(doc.pages[0], doc.pages[1]) == {
            "status": "continued", "signs": ["columns_match"],
        }
    finally:
        doc.close()


def test_header_repeated_and_columns(tmp_path):
    widths = [120, 80, 80]
    rows = _rows("Name", 8)
    doc = _open(tmp_path, "header.pdf", [
        [_table(300, widths, rows)],
        [_table(800, widths, rows)],
    ])
    try:
        found = judge(doc.pages[0], doc.pages[1])
    finally:
        doc.close()
    assert found["signs"] == ["header_repeated", "columns_match"]


def test_continued_word(tmp_path):
    doc = _open(tmp_path, "word.pdf", [
        [_table(300, [120, 80, 80], _rows("Old", 8))],
        [
            {"op": "text", "x": 72, "y": 820, "text": "Figure 24: Valuation (continued)"},
            _table(800, [90, 90, 90], _rows("Other", 8)),
        ],
    ])
    try:
        found = judge(doc.pages[0], doc.pages[1])
    finally:
        doc.close()
    assert found["status"] == "continued"
    assert found["signs"] == ["continued_word"]


def test_word_inside_sentence_not_a_sign(tmp_path):
    line = {"op": "text", "x": 72, "y": 800, "text": "Growth continued to slow in 3Q."}
    doc = _open(tmp_path, "sentence.pdf", [[line], [line]])
    try:
        assert judge(doc.pages[0], doc.pages[1]) == {"status": "none", "signs": []}
    finally:
        doc.close()


def test_runs_over_but_columns_differ_unclear(tmp_path):
    doc = _open(tmp_path, "unclear.pdf", [
        [_table(300, [120, 80, 80], _rows("Old", 8))],
        [_table(800, [90, 90, 90], _rows("New", 8))],
    ])
    try:
        assert judge(doc.pages[0], doc.pages[1]) == {"status": "unclear", "signs": []}
    finally:
        doc.close()


def test_prev_table_ends_mid_page_none(tmp_path):
    doc = _open(tmp_path, "mid.pdf", [
        [_table(600, [120, 80, 80], _rows("Old", 4))],
        [_table(800, [90, 90, 90], _rows("New", 8))],
    ])
    try:
        assert judge(doc.pages[0], doc.pages[1]) == {"status": "none", "signs": []}
    finally:
        doc.close()


def test_no_tables_none(tmp_path):
    doc = _open(tmp_path, "none.pdf", [
        text_lines(body(8)),
        text_lines(body(8)),
    ])
    try:
        assert judge(doc.pages[0], doc.pages[1]) == {"status": "none", "signs": []}
    finally:
        doc.close()


def test_continued_line_forms():
    assert has_continued_line(["Figure 24 (continued)"]) is True
    assert has_continued_line(["Table 3 (cont'd)"]) is True
    assert has_continued_line(["Continued"]) is True
    assert has_continued_line(["growth continued to slow"]) is False
