"""Each page is written or scanned. The caller passes the visible page."""

from __future__ import annotations

MIN_CHARS = 30
FULL_PAGE_IMAGE_SHARE = 0.85
MIN_LETTER_WORDS = 20
SPLIT_LETTER_SHARE = 0.30
BROKEN_WORD_SHARE = 0.05

_KEEP = {"a", "i"}


def image_share(page) -> float:
    images = page.images
    if not images:
        return 0.0
    page_area = page.width * page.height
    if page_area <= 0:
        return 0.0
    x0, top, x1, bottom = page.bbox
    best = 0.0
    for image in images:
        left = max(image["x0"], x0)
        upper = max(image["top"], top)
        right = min(image["x1"], x1)
        lower = min(image["bottom"], bottom)
        width = right - left
        height = lower - upper
        if width > 0 and height > 0:
            best = max(best, width * height)
    return best / page_area


def split_letter_share(words: list[str]) -> float:
    letters = [word for word in words if word.isalpha()]
    if len(letters) < MIN_LETTER_WORDS:
        return 0.0
    split = [word for word in letters if len(word) == 1 and word.casefold() not in _KEEP]
    return len(split) / len(letters)


def broken_word_share(words) -> float:
    if not words:
        return 0.0
    broken = sum(1 for word in words if "\ufffd" in word or "(cid:" in word)
    return broken / len(words)


def classify(visible) -> tuple[str, str]:
    chars = sum(1 for char in visible.chars if str(char.get("text", "")).strip())
    if chars < MIN_CHARS:
        return ("scanned", "no_text")
    if image_share(visible) >= FULL_PAGE_IMAGE_SHARE:
        return ("scanned", "full_page_image")
    words = [word["text"] for word in visible.extract_words()]
    if split_letter_share(words) > SPLIT_LETTER_SHARE:
        return ("scanned", "split_letters")
    if broken_word_share(words) > BROKEN_WORD_SHARE:
        return ("scanned", "broken_words")
    return ("written", "clean_text")
