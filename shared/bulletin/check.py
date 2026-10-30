"""The bulletin's code checks (docs/BULLETIN_PLAN.md slice 4). No model here.

    missing_in_sources(text, [source texts])   numbers of an item that no cited source has
    same_numbers(english, turkish)             the Turkish item has exactly the English item's numbers
    style_problem(text)                        advice, ratings and price targets are not news (roadmap "Morning bulletin" 4)

A number is read in both the English (`7,743.98`, `3.6%`) and the Turkish (`7.743,98`, `%3,6`) way. A token such as `1.000` may be
a thousand or a decimal one, so a token stands for a set of values; two numbers match when their sets share a value AND what stands
with them does not contradict: an explicit sign (`-5%` is not `+5%`), a scale word (million ≠ billion; milyon = million), a unit (`%` ≠
basis points) and a currency sign. A missing sign, scale, unit or currency on one side is not a contradiction ("fell 5%" matches "-5%").
Plain years (1900–2100) are not checked against sources; ordinals ("3rd", "3. çeyrek"), tenors ("2-year", "10 yıllık") and times of day
("15:30") are ignored (codex test of 2026-10-30: the first version ignored signs, scales and units).
"""

from __future__ import annotations

import re
from typing import NamedTuple

TOKEN = re.compile(r"(?<![\w.,])\d[\d.,]*\d|(?<![\w.,])\d")
YEAR = re.compile(r"^(19|20)\d\d$")
# ordinals are words, not figures: "3rd quarter" and the Turkish "3. çeyrek" (a dot and a lower-case word after it) carry no number
ORDINAL = re.compile(r"(?<![\w.,])\d{1,2}(?:st|nd|rd|th)\b|(?<![\w.,])\d{1,2}\.(?=\s+[a-zçğıöşü])")

# a tenor is a name, not a figure: "10-year", "2-year", "3-month" and the Turkish "10 yıllık", "3 aylık" (two digits at most, hyphen or "Y")
TENOR = re.compile(r"(?<![\w.,])\d{1,2}(?:-(?:year|yr|month|week|day)s?\b|\s?(?:yıllık|aylık|haftalık|günlük)\b|(?:Y|yr)\b)", re.IGNORECASE)

# a time of day is a clock reading, not a figure: "15:30", "8:30 ET"
TIME = re.compile(r"(?<![\w.,:])\d{1,2}:\d{2}(?::\d{2})?(?![\w.,:]*\d)")

# analyst ratings, targets and advice are not what the bulletin is for
STYLE = re.compile(r"\b(price targets?|target price|upgraded|downgraded|downgrades?|upgrades?|buy rating|sell rating|"
                   r"overweight|underweight|outperform|underperform|you should|should (?:buy|sell)|recommend(?:s|ed)? (?:buying|selling)|"
                   r"we recommend|i recommend|strong (?:buy|sell)|(?:buy|sell) now|worth buying|is a (?:buy|sell)|"
                   # Turkish advice (a translation must not add it): "satın alın", "hemen alın", "alım / satış tavsiyesi", "tavsiye ederiz"
                   r"satın al(?:ın|ınız|malısınız|manızı)|hemen (?:al|sat)(?:ın|ınız)?|alım tavsiyesi|satış tavsiyesi|tavsiye ed\w+|hedef fiyat)\b",
                   re.IGNORECASE)
# a sentence that starts with an order to trade: "Buy Apple now.", "Sell Tesla."
ORDER = re.compile(r"(?:^|[.!?]\s+)(?:buy|sell|short|accumulate|avoid|dump)\b", re.IGNORECASE)


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


SIGNS = "+-−–"
CURRENCIES = "$€£¥"
SCALE_WORDS = {"thousand": 3, "bin": 3, "k": 3, "million": 6, "milyon": 6, "mn": 6, "mln": 6, "billion": 9, "milyar": 9, "bn": 9, "bln": 9,
               "trillion": 12, "trilyon": 12, "tn": 12}
SCALE = re.compile(r"\s?(" + "|".join(sorted(SCALE_WORDS, key=len, reverse=True)) + r")(?![A-Za-z0-9çğıöşüÇĞİÖŞÜ])", re.IGNORECASE)
BASIS = re.compile(r"\s?(?:bps?\b|basis points?\b|baz puan)", re.IGNORECASE)
PERCENT_AFTER = re.compile(r"\s?(?:%|percent\b)", re.IGNORECASE)
PERCENT_BEFORE = re.compile(r"(?:yüzde|percent)\s*$", re.IGNORECASE)


class Num(NamedTuple):
    token: str
    values: frozenset
    sign: int = 0            # -1 / +1 only when printed right next to the digits ("-5%", "%-5", "+0.3"); 0 = none
    scale: int = 0           # 3 thousand · 6 million · 9 billion · 12 trillion (words in both languages); 0 = none
    unit: str = ""           # "pct" or "bp"
    cur: str = ""            # a currency sign printed before the number


def _clean(text: str) -> str:
    return TIME.sub(" ", TENOR.sub(" ", ORDINAL.sub(" ", text or "")))


def facts(text: str, skip_years: bool = False) -> list[Num]:
    """The numbers of a text with what stands next to them."""
    clean = _clean(text)
    out = []
    for m in TOKEN.finditer(clean):
        token = m.group(0)
        if skip_years and YEAR.match(token):
            continue
        before, after = clean[:m.start()], clean[m.end():]
        stripped = before.rstrip(CURRENCIES + "%")
        marks = before[len(stripped):]
        sign = 0
        if stripped and stripped[-1] in SIGNS:
            head = stripped[:-1].rstrip("%")
            if not head or head[-1] in " (\n\t":
                sign = -1 if stripped[-1] in "-−–" else 1
        cur = next((c for c in reversed(marks) if c in CURRENCIES), "")
        unit = "pct" if ("%" in marks or PERCENT_BEFORE.search(before) or PERCENT_AFTER.match(after)) else "bp" if BASIS.match(after) else ""
        scale = SCALE_WORDS.get((SCALE.match(after) or [None, ""])[1].lower(), 0) if SCALE.match(after) else 0
        out.append(Num(token, candidates(token), sign, scale, unit, cur))
    return out


def numbers(text: str, skip_years: bool = False) -> list[tuple[str, frozenset]]:
    return [(f.token, f.values) for f in facts(text, skip_years)]


def compatible(a: Num, b: Num) -> bool:
    """The same figure: a shared value, and no contradiction in sign, scale, unit or currency (a missing one is no contradiction)."""
    return bool(a.values & b.values) and all(not (x and y and x != y) for x, y in ((a.sign, b.sign), (a.scale, b.scale), (a.unit, b.unit), (a.cur, b.cur)))


def _index(texts) -> dict:
    by_value: dict = {}
    for text in texts:
        for f in facts(text):
            for v in f.values:
                by_value.setdefault(v, []).append(f)
    return by_value


def _found(n: Num, by_value: dict) -> bool:
    return any(compatible(n, other) for v in n.values for other in by_value.get(v, ()))


def missing_in_sources(text: str, sources: list[str]) -> list[str]:
    """The numbers of `text` (years left out) that none of the source texts has."""
    index = _index(sources)
    return [n.token for n in facts(text, skip_years=True) if not _found(n, index)]


def same_numbers(english: str, turkish: str) -> bool:
    """Every number of one text is in the other, both ways (years included)."""
    a, b = facts(english), facts(turkish)
    index_a, index_b = _index([english]), _index([turkish])
    return all(_found(n, index_b) for n in a) and all(_found(n, index_a) for n in b)


ADVICE = re.compile(r"\b(you should|should (?:buy|sell)|we recommend|i recommend|buy now|sell now|strong (?:buy|sell)|"
                    r"satın al(?:ın|ınız)|hemen (?:al|sat)(?:ın|ınız)?)\b", re.IGNORECASE)


def advice_problem(text: str) -> str | None:
    """Plain advice or an order to trade. Narrower than `style_problem`: a post that REPORTS a rating ("Goldman upgraded Shell") may be
    summarised by the Eye; only the bulletin keeps ratings out."""
    found = ADVICE.search(text or "") or ORDER.search(text or "")
    return found.group(0).strip(" .!?").lower() if found else None


def style_problem(text: str) -> str | None:
    found = STYLE.search(text or "")
    if found:
        return found.group(0).lower()
    order = ORDER.search(text or "")
    return order.group(0).strip(" .!?").lower() + " …" if order else None
