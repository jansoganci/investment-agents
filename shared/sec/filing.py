"""A filing's text: reading it, picking the paragraphs the AI needs, and checking a quote word for word (phase 2).

    text = filing.html_to_text(html)
    parts = filing.excerpts(text, ["goodwill", "impairment"], max_chars=12000)
    filing.quote_in(text, "The Company recorded a $9.7 billion gain ...")   # True / False

Code checks every quote before anything is believed: an AI cannot invent a quote that passes.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

BLOCK = {"p", "div", "br", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6", "section", "ul", "ol"}
SKIP = {"script", "style", "head", "title", "ix:header"}
MIN_QUOTE = 20

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                         "−": "-", " ": " ", "​": ""})


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif tag in BLOCK:
            self.parts.append("\n")
        elif tag in ("td", "th"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(html: str) -> str:
    """Plain text, one paragraph per line (a table row is one line)."""
    parser = _Text()
    parser.feed(html)
    parser.close()
    text = "".join(parser.parts).translate(_QUOTES)
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def normalize(s: str) -> str:
    """For comparing: curly quotes and dashes unified, any whitespace one space, lower case."""
    return re.sub(r"\s+", " ", s.translate(_QUOTES)).strip().lower()


def quote_in(text: str, quote: str, min_chars: int = MIN_QUOTE) -> bool:
    """The quote appears in the filing word for word (case, spacing, quote marks and dashes aside)."""
    q = normalize(quote).strip(" .…\"'")
    return len(q) >= min_chars and q in normalize(text)


def excerpts(text: str, terms: list[str], max_chars: int = 12000, per_paragraph: int = 1500) -> list[str]:
    """The paragraphs that mention the terms most, in document order, up to `max_chars` in all."""
    terms = [t.lower() for t in terms if t]
    scored = []
    for i, para in enumerate(text.split("\n")):
        if len(para) < 40 and not (len(para) >= 8 and re.search(r"\d", para)):
            continue  # short prose is noise; a short line with a number is a table row (`Long-term debt 32,366 7,469`)
        low = para.lower()
        score = sum(low.count(t) for t in terms)
        if score:
            scored.append((score, i, para[:per_paragraph]))
    picked, used = [], 0
    for score, i, para in sorted(scored, key=lambda x: (-x[0], x[1])):
        if used + len(para) > max_chars:
            continue
        picked.append((i, para))
        used += len(para)
    return [p for _, p in sorted(picked)]


_NUMBER = re.compile(r"\(?\$?\s?\d[\d,]*(?:\.\d+)?\)?")
_PERIOD = re.compile(r"(three|six|nine|twelve) months ended|year ended|weeks ended|quarter ended|in (millions|thousands)"
                     r"|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.? \d{1,2}, \d{4}", re.I)
ROW_MAX = 200  # a table row or a header is short; a longer line is prose
_MONTHS = re.compile(r"(three|six|nine|twelve) months ended|year ended|weeks ended|quarter ended", re.I)
_YEARS_ONLY = re.compile(r"^(?:(?:19|20)\d\d\s*)+$")


def _shown(value: float) -> list[str]:
    """How a figure can be printed in a statement: in millions, then in thousands (only where it is a whole number)."""
    out = []
    for unit in (1e6, 1e3):
        x = abs(value) / unit
        if abs(x - round(x)) < 1e-6 and round(x) >= 100:  # under 3 digits a number is everywhere (a note number, a day)
            out.append(f"{round(x):,}")
    return out


def _first_number(line: str, pattern: re.Pattern) -> bool:
    first = _NUMBER.search(line)
    return bool(first) and bool(pattern.search(line[first.start():first.end() + 2]))


def _around(line: str, pattern: re.Pattern, reach: int = 150) -> str:
    """A sentence that holds the figure (no table row does): the part around it, cut at word boundaries."""
    m = pattern.search(line)
    a, b = max(0, m.start() - reach), min(len(line), m.end() + reach)
    a = line.rfind(" ", 0, a) + 1 if a else 0
    b = line.find(" ", b) if b < len(line) and line.find(" ", b) != -1 else len(line)
    return line[a:b]


def _header(lines: list[str], i: int, reach: int = 60) -> list[str]:
    """The nearest line above row `i` that names the period or the unit (and the years line under it), so the auditor sees
    which column is which."""
    for k in range(i - 1, max(-1, i - reach), -1):
        if len(lines[k]) <= ROW_MAX and _PERIOD.search(lines[k]):
            out = [lines[k]]
            if k + 1 < i and _YEARS_ONLY.match(lines[k + 1]):
                out.append(lines[k + 1])
            if not _MONTHS.search(lines[k]):  # a line of dates only: the "Six Months Ended" line above says which is which
                above = next((lines[j] for j in range(k - 1, max(-1, k - 4), -1)
                              if len(lines[j]) <= ROW_MAX and _MONTHS.search(lines[j])), None)
                if above:
                    out.insert(0, above)
            return out
    return []


def rows_with(text: str, values: list[float], max_chars: int = 4000, per_value: int = 2) -> list[str]:
    """The filing rows that print our figures (roadmap rule 41): each row with its period header and, for a row of bare
    numbers, the label line above it. Table rows (two or more numbers) come before sentences. Found by value, so the
    auditor sees the statement rows even where the labels differ from our search terms (GE). In document order."""
    lines = text.split("\n")
    picked: dict[int, list[str]] = {}
    used = 0
    for value in values:
        for shown in _shown(value):
            pattern = re.compile(r"(?<![\d.,])" + re.escape(shown) + r"(?![\d]|[.,]\d)")
            hits = [i for i, line in enumerate(lines) if pattern.search(line)]
            if not hits:
                continue
            table = [i for i in hits if len(lines[i]) <= ROW_MAX and len(_NUMBER.findall(lines[i])) >= 2]
            if table:  # a table row beats a sentence; a row where it is the first number (the current column) comes first
                hits = sorted(table, key=lambda i: (not _first_number(lines[i], pattern), i))
            for i in hits[:per_value]:
                if i in picked:
                    continue
                block = _header(lines, i)
                if i > 0 and not re.search(r"[A-Za-z]", lines[i]) and lines[i - 1] not in block:
                    block.append(lines[i - 1])  # a row of bare numbers: its label is the line above
                block.append(lines[i] if i in table else _around(lines[i], pattern))
                size = sum(len(b) + 1 for b in block)
                if used + size > max_chars:
                    continue
                picked[i] = block
                used += size
            break  # found in this unit: the other unit is not tried
    return ["\n".join(picked[i]) for i in sorted(picked)]


def _part_ok(text: str, part: str, min_part: int) -> bool:
    if not re.search(r"[A-Za-z]", part) and len(_NUMBER.findall(part)) >= 2:
        return quote_in(text, part, 1)  # a row of bare numbers (`(666) (535)`, `2026 2025`): short, but still word for word
    return quote_in(text, part, min_part)


def quote_ok(text: str, quote: str, min_chars: int = MIN_QUOTE, min_part: int = 12) -> bool:
    """A quote, or several rows separated by ` | ` or by line breaks (a figure spread over rows, or a row copied with its
    header from the rows by value, rule 42): every part appears in the filing word for word, and one part is a full quote."""
    parts = [p.strip() for p in re.split(r"\s\|\s|\n", quote) if p.strip()]
    if len(parts) <= 1 or quote_in(text, quote, min_chars):
        return quote_in(text, quote, min_chars)
    return any(len(normalize(p)) >= min_chars for p in parts) and all(_part_ok(text, p, min_part) for p in parts)
