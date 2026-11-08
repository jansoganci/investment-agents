"""Page images for the pages that will be read."""

from __future__ import annotations

from pathlib import Path

import pypdfium2
from PIL import Image

IMAGE_DPI = 200
BOTTOM_SHARE = 0.30


def render(doc, page_no: int) -> Image.Image:
    page = doc[page_no - 1]
    try:
        return page.render(scale=IMAGE_DPI / 72).to_pil()
    finally:
        page.close()


def save_images(pdf_path: Path, folder: Path, read_pages: list[int]) -> dict[int, dict]:
    doc = pypdfium2.PdfDocument(str(pdf_path))
    saved: dict[int, dict] = {}
    try:
        for number in read_pages:
            image = render(doc, number)
            name = f"page-{number:03d}.png"
            image.save(folder / name)
            previous_name = None
            if number >= 2:
                previous = render(doc, number - 1)
                width, height = previous.size
                top = round(height * (1 - BOTTOM_SHARE))
                strip = previous.crop((0, top, width, height))
                previous_name = f"page-{number - 1:03d}-bottom.png"
                strip.save(folder / previous_name)
            saved[number] = {"image": name, "prev_bottom_image": previous_name}
    finally:
        doc.close()
    return saved
