import pdfplumber

from agents.pdf_reader.visible import same_color, to_rgb, visible_page
from tests.pdf_reader.helpers import make_pdf


def _page(tmp_path, name, ops):
    pdf = tmp_path / name
    make_pdf(pdf, [ops])
    return pdfplumber.open(pdf)


def test_to_rgb_forms():
    assert to_rgb(0.749) == (0.749, 0.749, 0.749)
    assert to_rgb((0.5,)) == (0.5, 0.5, 0.5)
    assert to_rgb((1, 0, 0)) == (1.0, 0.0, 0.0)
    assert to_rgb((0, 0, 0, 1)) == (0.0, 0.0, 0.0)
    assert to_rgb((0, 0, 0, 0)) == (1.0, 1.0, 1.0)
    assert to_rgb(None) is None
    assert to_rgb("P1") is None
    assert to_rgb((2,)) is None
    assert to_rgb((0.1, 0.2)) is None


def test_same_color_threshold():
    assert same_color((0.753, 0.753, 0.753), (0.749, 0.749, 0.749)) is True
    assert same_color((0.85, 0.85, 0.85), (1.0, 1.0, 1.0)) is False


def test_grey_on_grey_dropped(tmp_path):
    doc = _page(tmp_path, "grey.pdf", [
        {"op": "rect", "x": 72, "y": 700, "w": 60, "h": 16, "color": ("gray", 0.749)},
        {"op": "text", "x": 75, "y": 704, "text": "#N/A", "size": 10, "color": ("gray", 0.753)},
        {"op": "text", "x": 72, "y": 650, "text": "Revenue 12.3", "size": 10, "color": ("gray", 0.0)},
    ])
    try:
        visible, dropped = visible_page(doc.pages[0])
        text = visible.extract_text() or ""
    finally:
        doc.close()
    assert "Revenue 12.3" in text
    assert "#N/A" not in text
    assert dropped == 4


def test_white_on_white_page_dropped(tmp_path):
    doc = _page(tmp_path, "white.pdf", [
        {"op": "text", "x": 72, "y": 700, "text": "HIDDEN", "size": 10, "color": ("gray", 1)},
    ])
    try:
        _visible, dropped = visible_page(doc.pages[0])
    finally:
        doc.close()
    assert dropped == 6


def test_light_grey_on_white_kept(tmp_path):
    doc = _page(tmp_path, "light.pdf", [
        {"op": "text", "x": 72, "y": 700, "text": "Kept", "size": 10, "color": ("gray", 0.85)},
    ])
    try:
        visible, dropped = visible_page(doc.pages[0])
        text = visible.extract_text() or ""
    finally:
        doc.close()
    assert "Kept" in text
    assert dropped == 0


def test_cmyk_and_rgb_compared_in_one_system(tmp_path):
    doc = _page(tmp_path, "cmyk.pdf", [
        {"op": "rect", "x": 72, "y": 700, "w": 200, "h": 20, "color": ("gray", 0.75)},
        {"op": "text", "x": 75, "y": 704, "text": "CMYK", "size": 10, "color": ("cmyk", 0, 0, 0, 0.25)},
        {"op": "rect", "x": 72, "y": 640, "w": 200, "h": 20, "color": ("gray", 0.75)},
        {"op": "text", "x": 75, "y": 644, "text": "RGB", "size": 10, "color": ("rgb", 0.75, 0.75, 0.75)},
    ])
    try:
        visible, dropped = visible_page(doc.pages[0])
        text = visible.extract_text() or ""
    finally:
        doc.close()
    assert "CMYK" not in text
    assert "RGB" not in text
    assert dropped == 7


def test_white_text_on_image_kept(tmp_path):
    doc = _page(tmp_path, "image.pdf", [
        {"op": "image", "x": 50, "y": 500, "w": 400, "h": 250},
        {"op": "text", "x": 80, "y": 600, "text": "TITLE", "size": 14, "color": ("gray", 1)},
    ])
    try:
        visible, dropped = visible_page(doc.pages[0])
        text = visible.extract_text() or ""
    finally:
        doc.close()
    assert "TITLE" in text
    assert dropped == 0


def test_smallest_fill_wins(tmp_path):
    doc = _page(tmp_path, "fills.pdf", [
        {"op": "rect", "x": 0, "y": 0, "w": 595.27, "h": 841.89, "color": ("gray", 0.2)},
        {"op": "rect", "x": 72, "y": 700, "w": 120, "h": 40, "color": ("gray", 1)},
        {"op": "text", "x": 80, "y": 712, "text": "GONE", "size": 10, "color": ("gray", 1)},
        {"op": "text", "x": 80, "y": 400, "text": "SEEN", "size": 10, "color": ("gray", 1)},
    ])
    try:
        visible, dropped = visible_page(doc.pages[0])
        text = visible.extract_text() or ""
    finally:
        doc.close()
    assert "GONE" not in text
    assert "SEEN" in text
    assert dropped == 4
