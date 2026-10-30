"""Nothing secret leaves in an error message (codex test, 2026-10-30: a provider's error text was passed on as it came).

    redact.clean("Incorrect API key provided: sk-abc123…")     →  "Incorrect API key provided: [hidden]"

Hidden: the value of any environment variable whose name has KEY, TOKEN, COOKIE, SECRET or PASSWORD (8+ characters), `sk-…` style keys,
`Bearer …` headers and any unbroken run of 32+ letters, digits, `-` or `_` (a token). Ordinary words and numbers are left as they are."""

from __future__ import annotations

import os
import re

HIDDEN = "[hidden]"
NAMES = ("KEY", "TOKEN", "COOKIE", "SECRET", "PASSWORD")
PATTERNS = (re.compile(r"\bsk-[A-Za-z0-9_\-]{6,}"), re.compile(r"(?i)\bBearer\s+\S+"), re.compile(r"[A-Za-z0-9_\-]{32,}"))


def clean(text: str | None) -> str:
    out = str(text or "")
    for name, value in os.environ.items():
        if value and len(value) >= 8 and any(word in name.upper() for word in NAMES):
            out = out.replace(value, HIDDEN)
    for pattern in PATTERNS:
        out = pattern.sub(HIDDEN, out)
    return out
