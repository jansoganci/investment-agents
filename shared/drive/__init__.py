"""The Drive folder `Investing/` (roadmap section 5). Flat: the sector is in the card header, not in the path.

Investing/
├── Inbox/      agent 1's daily list
├── Weekly/     weekly summaries
├── Backup/     nightly SQLite copies
└── Stocks/<TICKER> - <Company name>/card.md
"""

from __future__ import annotations

import re
from pathlib import Path

from shared import config

FOLDERS = ("Inbox", "Weekly", "Backup", "Stocks")


def root() -> Path:
    return config.drive_dir()


def inbox() -> Path:
    return root() / "Inbox"


def weekly() -> Path:
    return root() / "Weekly"


def backup_dir() -> Path:
    return root() / "Backup"


def stocks_dir() -> Path:
    return root() / "Stocks"


def _safe(text: str) -> str:
    # no path separators or characters Drive / macOS dislike; keep it readable
    text = re.sub(r'[/\\:*?"<>|]+', " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stock_dir(ticker: str, company: str) -> Path:
    return stocks_dir() / f"{_safe(ticker)} - {_safe(company)}"


def card_path(ticker: str, company: str) -> Path:
    return stock_dir(ticker, company) / "card.md"


def find_card(ticker: str) -> Path | None:
    """The card of a ticker, whatever the company name in the folder."""
    folder = stocks_dir()
    if not folder.is_dir():
        return None
    for d in sorted(folder.glob(f"{_safe(ticker)} - *")):
        card = d / "card.md"
        if card.is_file():
            return card
    return None


def ensure_folders() -> None:
    for name in FOLDERS:
        (root() / name).mkdir(parents=True, exist_ok=True)
