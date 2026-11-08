"""Invisible text is dropped. Only rects are fills (curves are not).

Text-render mode 3 (OCR layers) is not detected; scanned pages are not trusted anyway.

SAME_COLOR is 0.01. On the 0–1 scale that is about 2.5 of 255 steps, which the eye
cannot tell apart. The sample "#N/A" cells differ by 0.004 (text 0.753, fill 0.749).
The lightest real grey text on white differs by about 0.15 or more.

A single number from 0 to 1 is grey: (g, g, g). A number outside that range is rejected.
"""

from __future__ import annotations

SAME_COLOR = 0.01


def to_rgb(color) -> tuple[float, float, float] | None:
    if isinstance(color, bool):
        return None
    if isinstance(color, (int, float)):
        if not 0 <= color <= 1:
            return None
        grey = float(color)
        return (grey, grey, grey)
    if isinstance(color, str) or color is None or not isinstance(color, (tuple, list)):
        return None
    nums: list[float] = []
    for value in color:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
            return None
        nums.append(float(value))
    if len(nums) == 1:
        grey = nums[0]
        return (grey, grey, grey)
    if len(nums) == 3:
        return (nums[0], nums[1], nums[2])
    if len(nums) == 4:
        cyan, magenta, yellow, black = nums
        return ((1 - cyan) * (1 - black), (1 - magenta) * (1 - black), (1 - yellow) * (1 - black))
    return None


def same_color(a, b) -> bool:
    return max(abs(x - y) for x, y in zip(a, b, strict=True)) <= SAME_COLOR


def _one_number(color):
    if isinstance(color, bool) or not isinstance(color, (int, float)):
        return color
    return (float(color),)


def _box_holds(box: dict, cx: float, cy: float) -> bool:
    return box["x0"] <= cx <= box["x1"] and box["top"] <= cy <= box["bottom"]


def _area(box: dict) -> float:
    return (box["x1"] - box["x0"]) * (box["bottom"] - box["top"])


def is_invisible(char: dict, rects: list[dict], images: list[dict]) -> bool:
    text = to_rgb(_one_number(char["non_stroking_color"]))
    if text is None:
        return False
    cx = (char["x0"] + char["x1"]) / 2
    cy = (char["top"] + char["bottom"]) / 2
    if any(_box_holds(image, cx, cy) for image in images):
        return False
    fills = [rect for rect in rects if rect.get("fill") is True and _box_holds(rect, cx, cy)]
    if not fills:
        under = (1.0, 1.0, 1.0)
    else:
        under = to_rgb(_one_number(min(fills, key=_area)["non_stroking_color"]))
        if under is None:
            return False
    return same_color(text, under)


def visible_page(page) -> tuple:
    dropped = 0

    def keep(obj) -> bool:
        nonlocal dropped
        if obj.get("object_type") == "char" and is_invisible(obj, page.rects, page.images):
            if str(obj.get("text", "")).strip():
                dropped += 1
            return False
        return True

    filtered = page.filter(keep)
    filtered.objects
    return filtered, dropped
