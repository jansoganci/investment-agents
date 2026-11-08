"""Tables that run over more than one page.

Tables without ruling lines are not detected. Such a page gets "none", so the
manual trial checks this.
"""

from __future__ import annotations

import re

from agents.pdf_reader.disclosure import normalize

EDGE_SHARE = 0.25
COLUMN_TOLERANCE_PT = 3.0
CONTINUED_LINE = re.compile(
    r"(?:\(|\b)(?:continued|cont'd|cont\.)\)?\s*$",
    re.IGNORECASE,
)
_SIGN_ORDER = ("continued_word", "header_repeated", "columns_match")


def table_shapes(page) -> list[dict]:
    shapes = []
    for table in page.find_tables():
        columns = None
        for row in table.rows:
            cells = row.cells
            if cells and all(cell is not None for cell in cells):
                columns = [cell[0] for cell in cells] + [cells[-1][2]]
                break
        extracted = table.extract()
        header = [normalize(cell or "") for cell in extracted[0]] if extracted else []
        box = table.bbox
        shapes.append({
            "top": box[1],
            "bottom": box[3],
            "columns": columns,
            "header": header,
        })
    shapes.sort(key=lambda shape: shape["top"])
    return shapes


def has_continued_line(lines: list[str]) -> bool:
    return any(CONTINUED_LINE.search(line) for line in lines)


def top_lines(page) -> list[str]:
    height = page.height * EDGE_SHARE
    cropped = page.crop((0, 0, page.width, height))
    return (cropped.extract_text() or "").split("\n")


def columns_match(a, b) -> bool:
    if a is None or b is None or len(a) != len(b) or len(a) < 3:
        return False
    return all(abs(left - right) <= COLUMN_TOLERANCE_PT for left, right in zip(a, b))


def header_repeated(a, b) -> bool:
    left, right = a["header"], b["header"]
    filled = [cell for cell in left if cell]
    return left == right and len(filled) >= 2


def judge(prev, cur) -> dict:
    flags = {
        "continued_word": has_continued_line(top_lines(cur)),
        "header_repeated": False,
        "columns_match": False,
    }
    previous = table_shapes(prev)
    current = table_shapes(cur)
    runs_over = False
    if previous and current:
        last = previous[-1]
        first = current[0]
        runs_over = (
            last["bottom"] >= prev.height * 0.75
            and first["top"] <= cur.height * 0.25
        )
        flags["header_repeated"] = header_repeated(last, first)
        flags["columns_match"] = runs_over and columns_match(last["columns"], first["columns"])
    signs = [name for name in _SIGN_ORDER if flags[name]]
    if signs:
        status = "continued"
    elif previous and current and runs_over:
        status = "unclear"
    else:
        status = "none"
    return {"status": status, "signs": signs}
