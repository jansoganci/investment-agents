"""Step 2, the page sorter. It writes pages.json and the page images."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import pypdfium2

from agents.pdf_reader import files, paths
from agents.pdf_reader.continuation import judge
from agents.pdf_reader.disclosure import find_start, sections_on_page
from agents.pdf_reader.images import save_images
from agents.pdf_reader.pagekind import classify
from agents.pdf_reader.visible import visible_page


def toc_entries(doc) -> list[tuple[str, int]]:
    found = []
    for item in doc.get_toc():
        if hasattr(item, "get_title"):
            title = item.get_title()
            dest = item.get_dest()
            index = None if dest is None else dest.get_index()
        else:
            title = item.title
            index = item.page_index
        if index is None:
            continue
        found.append((title, index + 1))
    return found


def _continuation(number: int, read: bool, kind: str, prev_kind: str | None, judged, previous: dict | None) -> dict:
    if number == 1 or not read:
        return {"status": "none", "header_from_page": None, "signs": []}
    if kind == "scanned" or prev_kind == "scanned":
        return {"status": "not_checked", "header_from_page": None, "signs": []}
    status = judged["status"]
    header = None
    if status == "continued":
        earlier = previous["continuation"]
        header = earlier["header_from_page"] if earlier["status"] == "continued" else number - 1
    return {"status": status, "header_from_page": header, "signs": judged["signs"]}


def sort_pdf(pdf_path: Path, work_dir: Path, fingerprint: str, source_name: str, now: datetime) -> dict:
    work_dir.mkdir(parents=True, exist_ok=True)
    pdfium = pypdfium2.PdfDocument(str(pdf_path))
    try:
        toc = toc_entries(pdfium)
    finally:
        pdfium.close()

    gathered = []
    with pdfplumber.open(pdf_path) as pdf:
        prev_visible = None
        prev_kind = None
        for number, page in enumerate(pdf.pages, start=1):
            visible, dropped = visible_page(page)
            kind, reason = classify(visible)
            text = visible.extract_text() or ""
            judged = None
            if number >= 2 and kind == "written" and prev_kind == "written":
                judged = judge(prev_visible, visible)
            gathered.append({
                "page": number,
                "kind": kind,
                "kind_reason": reason,
                "lines": text.split("\n"),
                "text": text,
                "dropped_invisible": dropped,
                "judged": judged,
            })
            prev_visible = visible
            prev_kind = kind

    start = find_start(toc, [item["lines"] for item in gathered])
    notes = []
    if start is None:
        notes.append({"code": "disclosure_start_not_found", "page": None})
    pages = []
    for index, item in enumerate(gathered):
        number = item["page"]
        part = "disclosure" if start is not None and number >= start["page"] else "content"
        if part == "content":
            read = True
            read_sections = ["all"]
        else:
            sections = sections_on_page(item["lines"])
            read = bool(sections)
            read_sections = sorted({section["section"] for section in sections})
            for section in sections:
                if section["only_link"]:
                    notes.append({
                        "code": f"{section['section']}_only_link",
                        "page": number,
                    })
        previous = pages[-1] if pages else None
        prev_kind = gathered[index - 1]["kind"] if index else None
        pages.append({
            "page": number,
            "kind": item["kind"],
            "kind_reason": item["kind_reason"],
            "part": part,
            "read": read,
            "read_sections": read_sections,
            "text": item["text"] if read and item["kind"] == "written" else None,
            "dropped_invisible": item["dropped_invisible"],
            "image": None,
            "prev_bottom_image": None,
            "continuation": _continuation(number, read, item["kind"], prev_kind, item["judged"], previous),
        })

    saved = save_images(pdf_path, work_dir, [page["page"] for page in pages if page["read"]])
    for page in pages:
        info = saved.get(page["page"])
        if info is not None:
            page["image"] = info["image"]
            page["prev_bottom_image"] = info["prev_bottom_image"]

    content = [page for page in pages if page["part"] == "content"]
    disclosure = [page for page in pages if page["part"] == "disclosure"]
    result = {
        "version": 1,
        "fingerprint": fingerprint,
        "source_name": source_name,
        "sorted_at": files.utc_stamp(now),
        "page_count": len(pages),
        "disclosure_start": start,
        "notes": notes,
        "counts": {
            "content": len(content),
            "content_written": sum(page["kind"] == "written" for page in content),
            "content_scanned": sum(page["kind"] == "scanned" for page in content),
            "disclosure": len(disclosure),
            "disclosure_read": sum(page["read"] for page in disclosure),
            "images": sum(page["image"] is not None for page in pages),
            "dropped_invisible": sum(page["dropped_invisible"] for page in pages),
        },
        "pages": pages,
    }
    files.write_json(work_dir / "pages.json", result)
    return result


def run(work_dir: Path, now: datetime | None = None) -> dict:
    if now is None:
        now = datetime.now(timezone.utc)
    queue = files.read_json(work_dir / "queue.json")
    pdf = paths.new_dir() / queue["source_name"]
    if not pdf.is_file():
        raise FileNotFoundError(pdf)
    return sort_pdf(pdf, work_dir, queue["fingerprint"], queue["source_name"], now)
