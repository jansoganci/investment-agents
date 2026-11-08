"""Small PDFs the tests build themselves. A bank PDF is never read here."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

_SENTENCES = (
    "Revenue grew 12% in FY26E as memory demand stayed strong.",
    "Gross margin improved to 41.5% on better product mix.",
    "Management kept its full-year guidance unchanged.",
    "Inventory days fell for the third quarter in a row.",
)


def body(n: int = 12) -> list[str]:
    return [_SENTENCES[i % 4] for i in range(n)]


def text_lines(
    lines: list[str], *, x: float = 72, top: float = 780, step: float = 14,
    size: float = 10, color: tuple = ("gray", 0.0),
) -> list[dict]:
    return [
        {"op": "text", "x": x, "y": top - i * step, "text": line, "size": size, "color": color}
        for i, line in enumerate(lines)
    ]


def gray_png(path: Path, size: tuple[int, int] = (400, 560), level: int = 180) -> Path:
    Image.new("L", size, level).save(path)
    return path


def garbage_pdf(path: Path) -> Path:
    path.write_bytes(b"%PDF-1.4\n%garbage\n" + b"x" * 200)
    return path


def _fill(c: canvas.Canvas, color: tuple) -> None:
    kind = color[0]
    if kind == "gray":
        c.setFillGray(color[1])
    elif kind == "rgb":
        c.setFillColorRGB(*color[1:])
    elif kind == "cmyk":
        c.setFillColorCMYK(*color[1:])
    else:
        raise ValueError(f"unknown color {color!r}")


def _draw(c: canvas.Canvas, pdf: Path, op: dict) -> None:
    kind = op["op"]
    if kind == "text":
        c.setFont("Helvetica", op.get("size", 10))
        _fill(c, op.get("color", ("gray", 0.0)))
        c.drawString(op["x"], op["y"], op["text"])
    elif kind == "rect":
        _fill(c, op["color"])
        c.rect(op["x"], op["y"], op["w"], op["h"], stroke=0, fill=1)
    elif kind == "image":
        img = pdf.with_name(f"{pdf.stem}-img.png")
        gray_png(img)
        c.drawImage(str(img), op["x"], op["y"], op["w"], op["h"])
    elif kind == "table":
        _table(c, op)
    else:
        raise ValueError(f"unknown op {kind!r}")


def _table(c: canvas.Canvas, op: dict) -> None:
    x = op["x"]
    top = op["top"]
    widths: list[float] = op["col_widths"]
    row_h = op["row_height"]
    rows: list[list] = op["rows"]
    height = row_h * len(rows)
    width = sum(widths)
    bottom = top - height
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    for i in range(len(rows) + 1):
        y = top - i * row_h
        c.line(x, y, x + width, y)
    edge = x
    for col in widths:
        c.line(edge, bottom, edge, top)
        edge += col
    c.line(edge, bottom, edge, top)
    c.setFillGray(0)
    c.setFont("Helvetica", 9)
    for i, row in enumerate(rows):
        row_bottom = top - (i + 1) * row_h
        cell_x = x
        for text, col in zip(row, widths, strict=True):
            c.drawString(cell_x + 3, row_bottom + 5, str(text))
            cell_x += col


def make_pdf(
    path: Path, pages: list[list[dict]], *,
    encrypt: str | None = None, bookmarks: list[tuple[str, int]] | None = None,
) -> Path:
    c = canvas.Canvas(str(path), pagesize=A4, encrypt=encrypt)
    marks = list(bookmarks or [])
    for number, ops in enumerate(pages, start=1):
        for op in ops:
            _draw(c, path, op)
        for i, (title, page_no) in enumerate(marks):
            if page_no == number:
                c.bookmarkPage(f"b{i}")
                c.addOutlineEntry(title, f"b{i}", level=0)
        c.showPage()
    c.save()
    return path
