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


def quote_ok(text: str, quote: str, min_chars: int = MIN_QUOTE, min_part: int = 12) -> bool:
    """A quote, or several rows separated by ` | ` (a figure spread over rows): every part appears in the filing word for word."""
    parts = [p.strip() for p in re.split(r"\s\|\s", quote) if p.strip()]
    if len(parts) <= 1:
        return quote_in(text, quote, min_chars)
    return all(quote_in(text, p, min_part) for p in parts)
