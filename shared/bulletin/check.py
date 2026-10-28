"""The bulletin's code checks (docs/BULLETIN_PLAN.md slice 4). No model here.

    missing_in_sources(text, [source texts])   numbers of an item that no cited source has
    same_numbers(english, turkish)             the Turkish item has exactly the English item's numbers
    style_problem(text)                        advice, ratings and price targets are not news (roadmap "Morning bulletin" 4)

A number is read in both the English (`7,743.98`, `3.6%`) and the Turkish (`7.743,98`, `%3,6`) way. A token such as `1.000` may be
a thousand or a decimal one, so a token stands for a set of values; two numbers match when their sets share a value. Plain years
(1900–2100) are not checked against sources; units, signs and ordinals ("3rd", "3. çeyrek") are ignored.
"""

from __future__ import annotations

import re

TOKEN = re.compile(r"(?<![\w.,])\d[\d.,]*\d|(?<![\w.,])\d")
YEAR = re.compile(r"^(19|20)\d\d$")
# ordinals are words, not figures: "3rd quarter" and the Turkish "3. çeyrek" (a dot and a lower-case word after it) carry no number
ORDINAL = re.compile(r"(?<![\w.,])\d{1,2}(?:st|nd|rd|th)\b|(?<![\w.,])\d{1,2}\.(?=\s+[a-zçğıöşü])")

# analyst ratings, targets and advice are not what the bulletin is for
STYLE = re.compile(r"\b(price targets?|target price|upgraded|downgraded|downgrades?|upgrades?|buy rating|sell rating|"
                   r"overweight|underweight|outperform|underperform|you should|should (?:buy|sell)|recommend(?:s|ed)? (?:buying|selling))\b",
                   re.IGNORECASE)


def _f(text: str) -> float:
    return round(float(text), 6)


def candidates(token: str) -> frozenset:
    """The values a number token can stand for."""
    dots, commas = token.count("."), token.count(",")
    if dots and commas:                                    # 7.743,98 or 7,743.98: the last separator is the decimal one
        last = max(token.rfind("."), token.rfind(","))
        return frozenset({_f(re.sub(r"[.,]", "", token[:last]) + "." + token[last + 1:])})
    if not dots and not commas:
        return frozenset({_f(token)})
    parts = token.split("." if dots else ",")
    if len(parts) > 2:                                     # 1.234.567 / 1,234,567: thousands separators
        return frozenset({_f("".join(parts))})
    whole, fraction = parts
    if len(fraction) == 3 and whole != "0" and len(whole) <= 3:      # 1.000 / 1,000: a thousand or a decimal
        return frozenset({_f(whole + fraction), _f(whole + "." + fraction)})
    return frozenset({_f(whole + "." + fraction)})


def numbers(text: str, skip_years: bool = False) -> list[tuple[str, frozenset]]:
    out = []
    for m in TOKEN.finditer(ORDINAL.sub(" ", text or "")):
        token = m.group(0)
        if skip_years and YEAR.match(token):
            continue
        out.append((token, candidates(token)))
    return out


def _pool(texts) -> set:
    pool: set = set()
    for text in texts:
        for _token, values in numbers(text):
            pool |= values
    return pool


def missing_in_sources(text: str, sources: list[str]) -> list[str]:
    """The numbers of `text` (years left out) that none of the source texts has."""
    pool = _pool(sources)
    return [token for token, values in numbers(text, skip_years=True) if not values & pool]


def same_numbers(english: str, turkish: str) -> bool:
    """Every number of one text is in the other, both ways (years included)."""
    a, b = numbers(english), numbers(turkish)
    pool_a, pool_b = set().union(*(v for _t, v in a)) if a else set(), set().union(*(v for _t, v in b)) if b else set()
    return all(v & pool_b for _t, v in a) and all(v & pool_a for _t, v in b)


def style_problem(text: str) -> str | None:
    found = STYLE.search(text or "")
    return found.group(0).lower() if found else None
