"""Where the disclosures start, and the two parts that are still read."""

from __future__ import annotations

import re
import unicodedata

DISCLOSURE_HEADINGS = (
    "disclosure appendix",
    "important disclosures",
    "analyst certification",
    "required disclosures",
)
RATINGS_SIGNS = (
    "ratings distribution",
    "rating distribution",
    "distribution of ratings",
)
FIRST_POSSIBLE_PAGE = 2
RISKS_HEADING = re.compile(
    r"^(?:[^:]{1,60}: )?(?:key |investment )?risks(?: to (?:our )?(?:rating|price target|thesis|view))?$"
)
VALUATION_HEADING = re.compile(
    r"^(?:[^:]{1,60}: )?valuation methodology(?: and risks)?$"
)
URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
LINK_ONLY_MAX_WORDS = 60
SECTION_MAX_LINES = 15
_EDGE = " :.-–—|"


def normalize(line: str) -> str:
    text = unicodedata.normalize("NFKC", line).casefold()
    text = re.sub(r"\s+", " ", text).strip().strip(_EDGE).strip()
    return text


def is_disclosure_heading(line: str) -> bool:
    return normalize(line) in DISCLOSURE_HEADINGS


def is_caps_heading(line: str) -> bool:
    text = line.strip()
    if text != text.upper():
        return False
    if not any(char.isalpha() for char in text):
        return False
    words = [word for word in text.split() if any(char.isalpha() for char in word)]
    return len(words) >= 2


def toc_start(toc: list[tuple[str, int]]) -> tuple[int, str] | None:
    found: tuple[int, str] | None = None
    for title, page in toc:
        if page < FIRST_POSSIBLE_PAGE:
            continue
        title_norm = normalize(title)
        if any(title_norm.startswith(heading) for heading in DISCLOSURE_HEADINGS):
            if found is None or page < found[0]:
                found = (page, title)
    return found


def _ratings_line(line: str) -> bool:
    text = normalize(line)
    return any(sign in text for sign in RATINGS_SIGNS)


def find_start(toc: list[tuple[str, int]], page_lines: list[list[str]]) -> dict | None:
    bookmark = toc_start(toc)
    if bookmark is not None:
        page, title = bookmark
        return {"page": page, "found_by": "bookmark", "text": title}
    for number, lines in enumerate(page_lines, start=1):
        if number < FIRST_POSSIBLE_PAGE:
            continue
        for line in lines:
            if is_disclosure_heading(line):
                return {"page": number, "found_by": "heading", "text": line.strip()}
    for number, lines in enumerate(page_lines, start=1):
        if number < FIRST_POSSIBLE_PAGE:
            continue
        for line in lines:
            if _ratings_line(line):
                return {"page": number, "found_by": "ratings_table", "text": line.strip()}
    return None


def _is_stop(line: str) -> bool:
    text = normalize(line)
    return (
        is_disclosure_heading(line)
        or VALUATION_HEADING.match(text) is not None
        or RISKS_HEADING.match(text) is not None
        or is_caps_heading(line)
    )


def _body(lines: list[str], start: int) -> str:
    taken: list[str] = []
    for line in lines[start:]:
        if _is_stop(line) or len(taken) >= SECTION_MAX_LINES:
            break
        taken.append(line)
    return " ".join(taken)


def _only_link(body: str) -> bool:
    if URL.search(body) is None:
        return False
    return len(URL.sub(" ", body).split()) <= LINK_ONLY_MAX_WORDS


def sections_on_page(lines: list[str]) -> list[dict]:
    found: list[dict] = []
    for index, line in enumerate(lines):
        text = normalize(line)
        body = _body(lines, index + 1)
        if VALUATION_HEADING.match(text):
            found.append({"section": "valuation", "line": index, "only_link": _only_link(body)})
            if text.endswith("and risks"):
                found.append({"section": "risks", "line": index, "only_link": _only_link(body)})
        elif RISKS_HEADING.match(text):
            found.append({"section": "risks", "line": index, "only_link": _only_link(body)})
    return found
