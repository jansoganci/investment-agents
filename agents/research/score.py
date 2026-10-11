"""The points of the five criteria (roadmap, "Score rules"). The AI sets labels; this code adds the points."""

from __future__ import annotations

CRITERIA = ("mentions", "tone", "sector_tailwind", "news_flow", "quick_health")


def tone_points(positive: int, negative: int) -> int:
    """net = positive − negative: ≤ −2 → 0, −1…+1 → 1 (mixed), ≥ +2 → 2."""
    net = positive - negative
    return 0 if net <= -2 else 2 if net >= 2 else 1


def news_points(serious_negative: bool, important_positive: bool, unclear: bool = False) -> int:
    """A confirmed serious negative → 0; none and an important positive → 2; otherwise 1 (also when the news could not be checked)."""
    if unclear:
        return 1
    if serious_negative:
        return 0
    return 2 if important_positive else 1


def total(points: dict) -> int:
    missing = [c for c in CRITERIA if c not in points]
    if missing:
        raise ValueError(f"no points for {', '.join(missing)}")
    return sum(points[c] for c in CRITERIA)
