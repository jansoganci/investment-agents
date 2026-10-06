"""When to consider selling (roadmap section 3): the triggers agent 3 watches, for stocks I hold only.

    1  the thesis broke (one of the card's "3 things that would break the thesis" happened)
    2  the grade fell to `weak`
    3  the grade was `solid`, then `mid` for 2 entries in a row

Never because the price fell. A single bad quarter is a "check now", not a trigger. The decision is mine.
"""

from __future__ import annotations

TRIGGERS = {"thesis_broken": "the thesis broke", "grade_weak": "the grade fell to weak",
            "mid_after_solid": "the grade was solid, then mid for 2 entries in a row"}


def trigger(in_portfolio: bool, grade: str, grades: list[str], thesis_status: str | None) -> str | None:
    """`grades`: the grades of the earlier entries, oldest first (not this one). Returns a key of TRIGGERS or None."""
    if not in_portfolio:
        return None
    if thesis_status == "broken":
        return "thesis_broken"
    previous = grades[-1] if grades else None
    if grade == "weak" and previous != "weak":
        return "grade_weak"
    if grade == "mid" and len(grades) >= 2 and grades[-1] == "mid" and grades[-2] == "solid":
        return "mid_after_solid"
    return None


def message(ticker: str, key: str, evidence: list[str], data_check_open: bool, held: str | None) -> str:
    """The text of the suggestion (it goes to Telegram through the analysis message)."""
    lines = []
    if held:
        lines.append(f"SELL SUGGESTION HELD · {ticker} — {TRIGGERS[key]}")
        lines.append(f"The auditor disagrees: {held}. It is not advice until the figures are checked.")
    else:
        lines.append(f"CONSIDER SELLING · {ticker} — {TRIGGERS[key]}")
        if data_check_open:
            lines.append("Check the figure before acting: a data check is open on this card.")
    lines += [f"- {e}" for e in evidence]
    lines.append("The decision is yours.")
    return "\n".join(lines)
