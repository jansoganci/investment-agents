import pdfplumber
from reportlab.lib.pagesizes import A4

from agents.pdf_reader.pagekind import broken_word_share, classify, split_letter_share
from tests.pdf_reader.helpers import body, make_pdf, text_lines


def _open(tmp_path, name, ops):
    pdf = tmp_path / name
    make_pdf(pdf, [ops])
    return pdfplumber.open(pdf)


def test_clean_page_written(tmp_path):
    doc = _open(tmp_path, "clean.pdf", text_lines(body(30)))
    try:
        assert classify(doc.pages[0]) == ("written", "clean_text")
    finally:
        doc.close()


def test_empty_page_scanned(tmp_path):
    doc = _open(tmp_path, "empty.pdf", [])
    try:
        assert classify(doc.pages[0]) == ("scanned", "no_text")
    finally:
        doc.close()


def test_few_chars_scanned(tmp_path):
    doc = _open(tmp_path, "few.pdf", text_lines(["Page 3"]))
    try:
        assert classify(doc.pages[0]) == ("scanned", "no_text")
    finally:
        doc.close()


def test_full_page_image_scanned(tmp_path):
    width, height = A4
    doc = _open(tmp_path, "full.pdf", [
        {"op": "image", "x": 0, "y": 0, "w": width, "h": height},
        *text_lines(body(20)),
    ])
    try:
        assert classify(doc.pages[0]) == ("scanned", "full_page_image")
    finally:
        doc.close()


def test_half_page_image_written(tmp_path):
    width, height = A4
    doc = _open(tmp_path, "half.pdf", [
        {"op": "image", "x": 0, "y": 0, "w": width, "h": height / 2},
        *text_lines(body(20)),
    ])
    try:
        assert classify(doc.pages[0])[0] == "written"
    finally:
        doc.close()


def test_split_letters_scanned(tmp_path):
    line = "p r o f i t  m a r g i n  r o s e"
    doc = _open(tmp_path, "split.pdf", text_lines([line] * 20))
    try:
        assert classify(doc.pages[0]) == ("scanned", "split_letters")
    finally:
        doc.close()


def test_split_letter_share_values():
    assert split_letter_share(["a", "I", "b"] * 10) == 10 / 30
    assert split_letter_share(["b"] * 19) == 0.0


def test_broken_word_share_boundary():
    share = broken_word_share(["(cid:12)abc", "\ufffdx"] + ["w"] * 38)
    assert share == 0.05
    assert not share > 0.05
