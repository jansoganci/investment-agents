import pdfplumber
import pypdfium2
import pytest

from tests.pdf_reader.helpers import body, make_pdf, text_lines


def test_make_pdf_two_pages_readable(tmp_path):
    pdf = tmp_path / "two.pdf"
    make_pdf(pdf, [text_lines(body(12)), text_lines(body(12))])
    with pdfplumber.open(pdf) as doc:
        assert len(doc.pages) == 2
        assert "Revenue grew 12%" in (doc.pages[0].extract_text() or "")


def test_encrypted_pdf_needs_password(tmp_path):
    pdf = tmp_path / "secret.pdf"
    make_pdf(pdf, [text_lines(body(4))], encrypt="secret")
    with pytest.raises(pypdfium2.PdfiumError) as caught:
        pypdfium2.PdfDocument(str(pdf))
    assert "password" in str(caught.value).lower()


def test_table_is_found(tmp_path):
    rows = [["a", "b", "c"], ["d", "e", "f"], ["g", "h", "i"]]
    pdf = tmp_path / "table.pdf"
    make_pdf(pdf, [[{
        "op": "table", "x": 72, "top": 300, "col_widths": [120, 80, 80],
        "row_height": 18, "rows": rows,
    }]])
    with pdfplumber.open(pdf) as doc:
        tables = doc.pages[0].find_tables()
        assert len(tables) == 1
        assert tables[0].extract() == rows


def _close(got, want) -> bool:
    if isinstance(got, bool):
        return False
    values = (float(got),) if isinstance(got, (int, float)) else tuple(got)
    return len(values) == len(want) and all(abs(a - b) < 1e-3 for a, b in zip(values, want))


def test_colors_are_float_tuples(tmp_path):
    pdf = tmp_path / "colors.pdf"
    make_pdf(pdf, [[
        {"op": "rect", "x": 72, "y": 700, "w": 60, "h": 16, "color": ("gray", 0.749)},
        {"op": "text", "x": 75, "y": 704, "text": "#N/A", "size": 10, "color": ("gray", 0.753)},
    ]])
    with pdfplumber.open(pdf) as doc:
        page = doc.pages[0]
        rect = page.rects[0]
        assert rect["fill"] is True
        assert _close(0.749, (0.749,))
        assert _close((0.749,), (0.749,))
        assert _close(rect["non_stroking_color"], (0.749,))
        assert _close(page.chars[0]["non_stroking_color"], (0.753,))
